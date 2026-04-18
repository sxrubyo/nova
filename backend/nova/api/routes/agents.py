"""Agent routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from nova.api.dependencies import get_current_workspace, get_kernel_dependency, to_payload
from nova.api.schemas.agent_schemas import AgentCreate, AgentUpdate
from nova.kernel import NovaKernel
from nova.storage.database import session_scope
from nova.storage.repositories.evaluation_repo import EvaluationRepository

router = APIRouter()


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
