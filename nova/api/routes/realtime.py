"""Realtime event feeds over WebSocket and SSE."""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from nova.api.dependencies import get_kernel_dependency
from nova.kernel import NovaKernel, get_kernel
from nova.storage.database import session_scope
from nova.storage.repositories.evaluation_repo import EvaluationRepository

router = APIRouter()


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, default=str)}\n\n"


async def _agent_metrics_payload(kernel: NovaKernel, agent_id: str) -> dict:
    agent = await kernel.agent_registry.get(agent_id)
    if agent is None:
        return {"error": "agent not found", "agent_id": agent_id}
    async with session_scope() as session:
        repo = EvaluationRepository(session)
        rows = await repo.list_by_agent(agent_id, limit=500)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_rows = [row for row in rows if row.created_at >= since]
    hour_counter = Counter(row.created_at.replace(minute=0, second=0, microsecond=0).isoformat() for row in recent_rows)
    action_counter = Counter(row.action for row in recent_rows)
    blocked = len([row for row in recent_rows if row.decision == "BLOCK"])
    avg_risk = round(sum(row.risk_score for row in recent_rows) / max(len(recent_rows), 1), 2)
    avg_duration = round(sum(row.duration_ms for row in recent_rows) / max(len(recent_rows), 1), 2)
    return {
        "agent_id": agent_id,
        "status": agent.status.value,
        "risk_score": avg_risk,
        "actions_count": len(recent_rows),
        "last_action": recent_rows[0].created_at.isoformat() if recent_rows else None,
        "memory_usage": None,
        "response_time_avg": avg_duration,
        "blocked_rate": round((blocked / max(len(recent_rows), 1)) * 100, 2),
        "most_common_actions": [{"action": action, "count": count} for action, count in action_counter.most_common(5)],
        "actions_per_hour": [{"hour": hour, "count": count} for hour, count in sorted(hour_counter.items())],
    }


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket) -> None:
    kernel = getattr(websocket.app.state, "kernel", None) or get_kernel()
    await kernel.initialize()
    await websocket.accept()
    queue = kernel.events.subscribe()
    try:
        for item in reversed(kernel.events.recent(20)):
            await websocket.send_json({"type": item.type, "payload": item.payload, "timestamp": item.timestamp.isoformat()})
        while True:
            event = await queue.get()
            await websocket.send_json({"type": event.type, "payload": event.payload, "timestamp": event.timestamp.isoformat()})
    except WebSocketDisconnect:
        pass
    finally:
        kernel.events.unsubscribe(queue)


@router.get("/api/stream/events")
async def stream_events(kernel: NovaKernel = Depends(get_kernel_dependency)) -> StreamingResponse:
    async def event_generator():
        queue = kernel.events.subscribe()
        try:
            for item in reversed(kernel.events.recent(20)):
                yield _sse({"type": item.type, "payload": item.payload, "timestamp": item.timestamp.isoformat()})
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield _sse({"type": event.type, "payload": event.payload, "timestamp": event.timestamp.isoformat()})
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            kernel.events.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/api/agents/{agent_id}/stream")
@router.get("/api/agents/{agent_id}/live")
async def agent_stream(agent_id: str, kernel: NovaKernel = Depends(get_kernel_dependency)) -> StreamingResponse:
    async def event_generator():
        while True:
            payload = await _agent_metrics_payload(kernel, agent_id)
            yield _sse(payload)
            await asyncio.sleep(5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
