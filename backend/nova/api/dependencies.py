"""Shared API dependencies."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import Depends, Header, HTTPException, Request

from nova.kernel import NovaKernel, get_kernel
from nova.workspace.permissions import decode_access_token


def to_payload(value: Any) -> Any:
    """Convert dataclasses and enums into JSON-friendly payloads."""

    if is_dataclass(value):
        return {key: to_payload(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: to_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_payload(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            return value
    return value


async def get_kernel_dependency(request: Request) -> NovaKernel:
    """Return the kernel stored on the app or the default singleton."""

    kernel = getattr(request.app.state, "kernel", None) or get_kernel()
    await kernel.initialize()
    return kernel


async def get_current_workspace(
    request: Request,
    kernel: NovaKernel = Depends(get_kernel_dependency),
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
) -> dict[str, Any]:
    """Resolve workspace identity from JWT or API key."""

    if x_api_key:
        workspace = await kernel.workspace_manager.get_by_api_key(x_api_key)
        if workspace is not None:
            return {"workspace_id": workspace.id, "email": workspace.owner_email, "role": workspace.role}
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            return decode_access_token(kernel.config, token)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=401, detail=f"invalid token: {exc}") from exc
    raise HTTPException(status_code=401, detail="authentication required")
