"""Workspace plan definitions."""

from __future__ import annotations

from nova.types import WorkspacePlan


class PlanManager:
    """Resolve plan-specific quotas and features."""

    PLAN_QUOTAS: dict[WorkspacePlan, int] = {
        WorkspacePlan.FREE: 1_000,
        WorkspacePlan.PRO: 10_000,
        WorkspacePlan.ENTERPRISE: 100_000,
    }

    def quota_for_plan(self, plan: WorkspacePlan) -> int:
        return self.PLAN_QUOTAS[plan]
