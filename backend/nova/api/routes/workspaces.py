"""Workspace routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from nova.api.dependencies import get_current_workspace, get_kernel_dependency, to_payload
from nova.api.schemas.auth_schemas import RegisterRequest
from nova.kernel import NovaKernel
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
