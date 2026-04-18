"""Authentication routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from nova.api.dependencies import get_current_workspace, get_kernel_dependency
from nova.api.schemas.auth_schemas import AuthResponse, LoginRequest, MeResponse, RegisterRequest
from nova.kernel import NovaKernel
from nova.types import WorkspacePlan
from nova.workspace.permissions import create_access_token, verify_password

router = APIRouter()


@router.post("/api/auth/register", response_model=AuthResponse)
async def register(payload: RegisterRequest, kernel: NovaKernel = Depends(get_kernel_dependency)) -> AuthResponse:
    workspace = await kernel.workspace_manager.create_workspace(
        name=payload.workspace_name,
        owner_email=payload.email,
        owner_name=payload.owner_name,
        password=payload.password,
        plan=WorkspacePlan(payload.plan),
    )
    token = create_access_token(
        kernel.config,
        subject=payload.email,
        claims={"workspace_id": workspace.id, "email": payload.email, "role": "admin"},
    )
    return AuthResponse(
        access_token=token,
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        api_key=workspace.api_key,
    )


@router.post("/api/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest, kernel: NovaKernel = Depends(get_kernel_dependency)) -> AuthResponse:
    workspace = await kernel.workspace_manager.get_by_email(payload.email)
    if workspace is None or not verify_password(payload.password, workspace.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = create_access_token(
        kernel.config,
        subject=payload.email,
        claims={"workspace_id": workspace.id, "email": workspace.owner_email, "role": workspace.role},
    )
    return AuthResponse(
        access_token=token,
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        api_key=workspace.api_key,
    )


@router.get("/api/auth/me", response_model=MeResponse)
async def me(current_workspace: dict = Depends(get_current_workspace)) -> MeResponse:
    return MeResponse(
        workspace_id=current_workspace["workspace_id"],
        email=current_workspace["email"],
        role=current_workspace["role"],
    )
