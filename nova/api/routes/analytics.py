"""Analytics routes."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from nova.api.dependencies import get_current_workspace, get_kernel_dependency
from nova.kernel import NovaKernel
from nova.storage.database import session_scope
from nova.storage.repositories.evaluation_repo import EvaluationRepository

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


@router.get("/api/alerts")
async def alerts(limit: int = Query(20, ge=1, le=100), _: dict = Depends(get_current_workspace), kernel: NovaKernel = Depends(get_kernel_dependency)) -> list[dict]:
    return kernel.alerts.recent(limit)


@router.get("/api/stats/agents")
async def stats_agents(
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> list[dict]:
    agents = await kernel.agent_registry.list(current_workspace["workspace_id"])
    async with session_scope() as session:
        repo = EvaluationRepository(session)
        rows = await repo.list_by_workspace(current_workspace["workspace_id"], limit=5000)
    grouped: dict[str, list] = {}
    for row in rows:
        grouped.setdefault(row.agent_id, []).append(row)
    payload = []
    for agent in agents:
        agent_rows = grouped.get(agent.id, [])
        total = len(agent_rows)
        blocked = len([row for row in agent_rows if row.decision == "BLOCK"])
        escalated = len([row for row in agent_rows if row.decision == "ESCALATE"])
        allowed = len([row for row in agent_rows if row.decision == "ALLOW"])
        avg_score = round(sum(row.risk_score for row in agent_rows) / max(total, 1), 2) if agent_rows else 0
        payload.append(
            {
                "agent_id": agent.id,
                "agent_name": agent.name,
                "provider": agent.provider,
                "model": agent.model,
                "status": agent.status.value,
                "total_actions": total,
                "blocked": blocked,
                "escalated": escalated,
                "approval_rate": round((allowed / max(total, 1)) * 100, 2) if total else 100.0,
                "avg_score": avg_score,
                "risk_score": avg_score,
                "last_action": agent_rows[0].created_at.isoformat() if agent_rows else None,
                "metadata": agent.metadata,
            }
        )
    return payload


@router.get("/api/stats/risk")
async def stats_risk(
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    return {"agents": await stats_agents(current_workspace=current_workspace, kernel=kernel)}


@router.get("/api/stats/timeline")
async def stats_timeline(
    hours: int = Query(24, ge=1, le=168),
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> list[dict]:
    async with session_scope() as session:
        repo = EvaluationRepository(session)
        rows = await repo.list_by_workspace(current_workspace["workspace_id"], limit=5000)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    buckets: dict[datetime, list] = {}
    for row in rows:
        if row.created_at < cutoff:
            continue
        bucket = row.created_at.replace(minute=0, second=0, microsecond=0)
        buckets.setdefault(bucket, []).append(row)
    payload = []
    for hour, items in sorted(buckets.items()):
        approved = len([row for row in items if row.decision == "ALLOW"])
        blocked = len([row for row in items if row.decision == "BLOCK"])
        payload.append(
            {
                "hour": hour.isoformat(),
                "total": len(items),
                "approved": approved,
                "blocked": blocked,
                "avg_score": round(sum(row.risk_score for row in items) / max(len(items), 1), 2),
            }
        )
    return payload
