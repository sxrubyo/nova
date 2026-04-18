"""Settings routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from nova.api.dependencies import get_current_workspace, get_kernel_dependency
from nova.kernel import NovaKernel

router = APIRouter()


@router.get("/api/settings")
async def settings(_: dict = Depends(get_current_workspace), kernel: NovaKernel = Depends(get_kernel_dependency)) -> dict:
    return kernel.config.public_dict()
