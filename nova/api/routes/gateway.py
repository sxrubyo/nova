"""Gateway routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from nova.api.dependencies import get_current_workspace, get_kernel_dependency
from nova.kernel import NovaKernel

router = APIRouter()


@router.get("/api/gateway/status")
async def gateway_status(_: dict = Depends(get_current_workspace), kernel: NovaKernel = Depends(get_kernel_dependency)) -> dict:
    return {"providers": kernel.gateway.status()}


@router.get("/api/gateway/latency")
async def gateway_latency(_: dict = Depends(get_current_workspace), kernel: NovaKernel = Depends(get_kernel_dependency)) -> dict:
    return {"latency_ms": kernel.metrics.provider_snapshot()}
