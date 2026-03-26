"""Workspace persistence helpers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nova.storage.models import WorkspaceModel


class WorkspaceRepository:
    """CRUD operations for workspaces."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[WorkspaceModel]:
        result = await self.session.execute(select(WorkspaceModel).order_by(WorkspaceModel.name))
        return list(result.scalars().all())

    async def get(self, workspace_id: str) -> WorkspaceModel | None:
        return await self.session.get(WorkspaceModel, workspace_id)

    async def get_by_slug(self, slug: str) -> WorkspaceModel | None:
        result = await self.session.execute(select(WorkspaceModel).where(WorkspaceModel.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> WorkspaceModel | None:
        result = await self.session.execute(select(WorkspaceModel).where(WorkspaceModel.owner_email == email))
        return result.scalar_one_or_none()

    async def get_by_api_key(self, api_key: str) -> WorkspaceModel | None:
        result = await self.session.execute(select(WorkspaceModel).where(WorkspaceModel.api_key == api_key))
        return result.scalar_one_or_none()

    async def create(self, workspace: WorkspaceModel) -> WorkspaceModel:
        self.session.add(workspace)
        await self.session.flush()
        return workspace

    async def increment_usage(self, workspace_id: str) -> None:
        workspace = await self.get(workspace_id)
        if workspace is None:
            return
        workspace.usage_this_month += 1
        await self.session.flush()
