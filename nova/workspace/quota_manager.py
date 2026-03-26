"""Quota management for workspaces."""

from __future__ import annotations

from nova.storage.database import session_scope
from nova.storage.repositories.workspace_repo import WorkspaceRepository


class QuotaManager:
    """Checks and increments workspace evaluation quotas."""

    async def check(self, workspace_id: str) -> bool:
        async with session_scope() as session:
            repo = WorkspaceRepository(session)
            workspace = await repo.get(workspace_id)
            return bool(workspace and workspace.usage_this_month < workspace.quota_monthly)

    async def increment(self, workspace_id: str) -> None:
        async with session_scope() as session:
            repo = WorkspaceRepository(session)
            await repo.increment_usage(workspace_id)
