"""Status routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from nova.api.dependencies import get_kernel_dependency, to_payload
from nova.kernel import NovaKernel

router = APIRouter()


@router.get("/api/status")
async def status(kernel: NovaKernel = Depends(get_kernel_dependency)) -> dict:
    return to_payload(await kernel.get_status())
