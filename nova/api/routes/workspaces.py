"""Workspace routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from nova.api.dependencies import get_current_workspace, get_kernel_dependency, to_payload
from nova.api.schemas.auth_schemas import RegisterRequest
from nova.kernel import NovaKernel
from nova.storage.database import session_scope
from nova.storage.repositories.evaluation_repo import EvaluationRepository
from nova.types import WorkspacePlan

router = APIRouter()


@router.get("/api/workspaces")
async def list_workspaces(
    kernel: NovaKernel = Depends(get_kernel_dependency),
    _: dict = Depends(get_current_workspace),
) -> list[dict]:
    return [to_payload(workspace) for workspace in await kernel.workspace_manager.list_workspaces()]


@router.post("/api/workspaces")
async def create_workspace(
    payload: RegisterRequest,
    kernel: NovaKernel = Depends(get_kernel_dependency),
    _: dict = Depends(get_current_workspace),
) -> dict:
    workspace = await kernel.workspace_manager.create_workspace(
        name=payload.workspace_name,
        owner_email=payload.email,
        owner_name=payload.owner_name,
        password=payload.password,
        plan=WorkspacePlan(payload.plan),
    )
    return to_payload(workspace)


@router.get("/api/workspaces/me")
async def current_workspace_detail(
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    workspace = await kernel.workspace_manager.get_workspace(current_workspace["workspace_id"])
    async with session_scope() as session:
        repo = EvaluationRepository(session)
        entries = await repo.list_by_workspace(current_workspace["workspace_id"], limit=2000)
    active_agents = len(await kernel.agent_registry.list(current_workspace["workspace_id"]))
    blocked = len([row for row in entries if row.decision == "BLOCK"])
    escalated = len([row for row in entries if row.decision == "ESCALATE"])
    avg_score = round(sum(row.risk_score for row in entries) / max(len(entries), 1), 2)
    approval_rate = round(((len(entries) - blocked - escalated) / max(len(entries), 1)) * 100, 2) if entries else 100.0
    return {
        **to_payload(workspace),
        "email": current_workspace["email"],
        "owner_name": workspace.name if workspace else "Workspace",
        "stats": {
            "total_actions": len(entries),
            "blocked": blocked,
            "escalated": escalated,
            "active_agents": active_agents,
            "approval_rate": approval_rate,
            "avg_score": avg_score,
            "alerts_pending": len(kernel.alerts.recent(50)),
        },
    }
