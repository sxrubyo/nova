"""Analytics routes."""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, Query

from nova.api.dependencies import get_current_workspace, get_kernel_dependency
from nova.kernel import NovaKernel

router = APIRouter()


@router.get("/api/analytics/summary")
async def analytics_summary(_: dict = Depends(get_current_workspace), kernel: NovaKernel = Depends(get_kernel_dependency)) -> dict:
    return kernel.metrics.summary()


@router.get("/api/analytics/risk-scores")
async def analytics_risk_scores(
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    entries = await kernel.ledger.list_entries(current_workspace["workspace_id"], 200)
    return {"scores": [entry.risk_score for entry in entries]}


@router.get("/api/analytics/actions")
async def analytics_actions(
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    entries = await kernel.ledger.list_entries(current_workspace["workspace_id"], 200)
    counts = Counter(entry.action_type for entry in entries)
    return {"actions": dict(counts)}


@router.get("/api/analytics/providers")
async def analytics_providers(_: dict = Depends(get_current_workspace), kernel: NovaKernel = Depends(get_kernel_dependency)) -> dict:
    return {"providers": kernel.metrics.provider_snapshot()}


@router.get("/api/analytics/anomalies")
async def analytics_anomalies(limit: int = Query(20, ge=1, le=100), _: dict = Depends(get_current_workspace), kernel: NovaKernel = Depends(get_kernel_dependency)) -> dict:
    return {"alerts": kernel.alerts.recent(limit)}
