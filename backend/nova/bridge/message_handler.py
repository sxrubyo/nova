"""Bridge message handling."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from nova.api.dependencies import to_payload
from nova.bridge.agent_session import AgentSession
from nova.bridge.protocol import BridgeMessage
from nova.types import EvaluationRequest


class MessageHandler:
    """Dispatch bridge messages to the Nova kernel."""

    def __init__(self, bridge: object) -> None:
        self.bridge = bridge

    async def handle(self, session: AgentSession, raw: dict) -> dict:
        message = BridgeMessage(**raw)
        if message.type == "heartbeat":
            self.bridge.heartbeat.touch(session)
            return {"type": "heartbeat_ack", "timestamp": datetime.now(timezone.utc).isoformat()}
        if message.type == "register":
            session.capabilities = message.capabilities
            self.bridge.heartbeat.touch(session)
            return {"type": "registered", "agent_id": session.agent_id, "session_id": session.session_id}
        if message.type == "evaluate":
            result = await self.bridge.kernel.evaluate(
                EvaluationRequest(
                    agent_id=message.agent_id or session.agent_id,
                    workspace_id=None,
                    action=message.action or "",
                    payload=message.payload,
                    source="bridge",
                )
            )
            return {"type": "evaluation_result", **to_payload(result)}
        return {"type": "error", "code": "UNKNOWN_MESSAGE", "message": f"unsupported type {message.type}"}
