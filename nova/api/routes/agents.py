"""Agent routes."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from nova.api.dependencies import get_current_workspace, get_kernel_dependency, to_payload
from nova.api.schemas.agent_schemas import AgentCreate, AgentUpdate, ManagedAgentCreate
from nova.kernel import NovaKernel
from nova.storage.database import session_scope
from nova.storage.repositories.evaluation_repo import EvaluationRepository

router = APIRouter()


@router.post("/api/agents/create")
async def create_managed_agent(
    payload: ManagedAgentCreate,
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    agent, connection = await kernel.discovery.create_managed_agent(
        workspace_id=payload.workspace_id or current_workspace["workspace_id"],
        name=payload.name,
        agent_type=payload.type,
        model=payload.model,
        config=payload.config,
        permissions=payload.permissions.model_dump(),
        risk_thresholds=payload.risk_thresholds.model_dump(),
        quota=payload.quota.model_dump(),
    )
    return {"agent": to_payload(agent), "connection": to_payload(connection) if connection else None}


@router.get("/api/agents")
async def list_agents(
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> list[dict]:
    return [to_payload(agent) for agent in await kernel.agent_registry.list(current_workspace["workspace_id"])]


@router.post("/api/agents")
async def create_agent(
    payload: AgentCreate,
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    agent = await kernel.agent_registry.create(
        workspace_id=current_workspace["workspace_id"],
        name=payload.name,
        model=payload.model,
        provider=payload.provider,
        description=payload.description,
        capabilities=payload.capabilities,
        permissions=payload.permissions,
        metadata=payload.metadata,
    )
    return to_payload(agent)


@router.get("/api/agents/{agent_id}")
async def get_agent(
    agent_id: str,
    _: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    agent = await kernel.agent_registry.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return to_payload(agent)


@router.put("/api/agents/{agent_id}")
async def update_agent(
    agent_id: str,
    payload: AgentUpdate,
    _: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    agent = await kernel.agent_registry.update(agent_id, **payload.model_dump(exclude_none=True))
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return to_payload(agent)


@router.delete("/api/agents/{agent_id}")
async def delete_agent(
    agent_id: str,
    _: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    deleted = await kernel.agent_registry.delete(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="agent not found")
    return {"deleted": True, "agent_id": agent_id}


@router.post("/api/agents/{agent_id}/pause")
async def pause_agent(agent_id: str, _: dict = Depends(get_current_workspace), kernel: NovaKernel = Depends(get_kernel_dependency)) -> dict:
    agent = await kernel.agent_registry.pause(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return to_payload(agent)


@router.post("/api/agents/{agent_id}/resume")
async def resume_agent(agent_id: str, _: dict = Depends(get_current_workspace), kernel: NovaKernel = Depends(get_kernel_dependency)) -> dict:
    agent = await kernel.agent_registry.resume(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return to_payload(agent)


@router.get("/api/agents/{agent_id}/logs")
async def agent_logs(agent_id: str, _: dict = Depends(get_current_workspace)) -> list[dict]:
    async with session_scope() as session:
        repo = EvaluationRepository(session)
        return [
            {
                "id": item.id,
                "action": item.action,
                "decision": item.decision,
                "risk_score": item.risk_score,
                "status": item.status,
                "created_at": item.created_at.isoformat(),
            }
            for item in await repo.list_by_agent(agent_id)
        ]


@router.get("/api/agents/{agent_id}/metrics")
async def agent_metrics(
    agent_id: str,
    _: dict = Depends(get_current_workspace),
) -> dict:
    async with session_scope() as session:
        repo = EvaluationRepository(session)
        rows = await repo.list_by_agent(agent_id, limit=2000)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_rows = [row for row in rows if row.created_at >= since]
    action_counter = Counter(row.action for row in recent_rows)
    blocked = len([row for row in recent_rows if row.decision == "BLOCK"])
    errored = len([row for row in recent_rows if row.status not in {"completed", "approved", "queued"}])
    hourly = Counter(row.created_at.replace(minute=0, second=0, microsecond=0).isoformat() for row in recent_rows)
    return {
        "actions_per_hour": [{"hour": hour, "count": count} for hour, count in sorted(hourly.items())],
        "avg_risk_score": round(sum(row.risk_score for row in recent_rows) / max(len(recent_rows), 1), 2),
        "blocked_rate": round((blocked / max(len(recent_rows), 1)) * 100, 2),
        "most_common_actions": [{"action": action, "count": count} for action, count in action_counter.most_common(5)],
        "error_rate": round((errored / max(len(recent_rows), 1)) * 100, 2),
        "response_time_avg": round(sum(row.duration_ms for row in recent_rows) / max(len(recent_rows), 1), 2),
    }
