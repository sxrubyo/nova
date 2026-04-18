"""WebSocket bridge for connected agents."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

import websockets

from nova.bridge.agent_session import AgentSession
from nova.bridge.heartbeat import HeartbeatManager
from nova.bridge.message_handler import MessageHandler
from nova.config import NovaConfig
from nova.observability.logger import get_logger
from nova.security.rate_limiter import RateLimiter
from nova.utils.crypto import generate_id


class NovaBridge:
    """Bridge server that accepts real-time evaluation traffic from agents."""

    def __init__(self, kernel: Any, config: NovaConfig) -> None:
        self.kernel = kernel
        self.config = config
        self.logger = get_logger("nova.bridge")
        self.heartbeat = HeartbeatManager()
        self.handler = MessageHandler(self)
        self.sessions: dict[str, AgentSession] = {}
        self.queues: dict[str, list[dict]] = {}
        self.rate_limiter = RateLimiter(config.rate_limit_per_minute)
        self._server: websockets.server.Serve | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._server = await websockets.serve(self._handle_connection, self.config.host, self.config.bridge_port)
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(), name="nova-bridge-heartbeat")

    async def stop(self) -> None:
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def status(self) -> dict:
        return {"sessions": len(self.sessions), "port": self.config.bridge_port}

    async def _handle_connection(self, websocket: Any) -> None:
        api_key = websocket.request_headers.get("x-api-key") or self._query_param(websocket.path, "api_key")
        agent_id = self._query_param(websocket.path, "agent_id") or generate_id("agent")
        if not api_key:
            await websocket.close(code=4401, reason="missing api key")
            return
        workspace = await self.kernel.workspace_manager.get_by_api_key(api_key)
        if workspace is None:
            await websocket.close(code=4403, reason="invalid api key")
            return
        session = AgentSession(session_id=generate_id("sess"), agent_id=agent_id, api_key=api_key, websocket=websocket)
        self.sessions[session.session_id] = session
        try:
            await self._flush_queue(session)
            async for message in websocket:
                if not self.rate_limiter.allow(session.session_id):
                    await websocket.send(json.dumps({"type": "error", "code": "RATE_LIMIT", "message": "rate limit exceeded"}))
                    continue
                payload = json.loads(message)
                response = await self.handler.handle(session, payload)
                await websocket.send(json.dumps(response))
        finally:
            self.queues[session.agent_id] = list(session.queue)
            self.sessions.pop(session.session_id, None)

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(30)
            for session in list(self.sessions.values()):
                try:
                    await session.websocket.send(json.dumps({"type": "heartbeat", "timestamp": datetime.now(timezone.utc).isoformat()}))
                    self.heartbeat.missed(session)
                    if self.heartbeat.stale(session):
                        await session.websocket.close(code=4410, reason="heartbeat timeout")
                except Exception:  # noqa: BLE001
                    with contextlib.suppress(Exception):
                        await session.websocket.close()

    async def _flush_queue(self, session: AgentSession) -> None:
        for message in self.queues.pop(session.agent_id, []):
            await session.websocket.send(json.dumps(message))

    def _query_param(self, path: str, key: str) -> str | None:
        query = urlparse(path).query
        values = parse_qs(query).get(key)
        return values[0] if values else None


import contextlib  # noqa: E402
