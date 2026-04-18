"""Agent persistence helpers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from nova.storage.models import AgentModel, WorkspaceModel


class AgentRepository:
    """CRUD operations for agents."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_workspace(self, workspace_id: str) -> list[AgentModel]:
        result = await self.session.execute(
            select(AgentModel)
            .where(AgentModel.workspace_id == workspace_id)
            .options(selectinload(AgentModel.workspace))
            .order_by(AgentModel.name)
        )
        return list(result.scalars().all())

    async def get(self, agent_id: str) -> AgentModel | None:
        result = await self.session.execute(
            select(AgentModel)
            .where(AgentModel.id == agent_id)
            .options(selectinload(AgentModel.workspace))
        )
        return result.scalar_one_or_none()

    async def get_by_workspace_and_name(self, workspace_id: str, name: str) -> AgentModel | None:
        result = await self.session.execute(
            select(AgentModel)
            .where(AgentModel.workspace_id == workspace_id, AgentModel.name == name)
            .options(selectinload(AgentModel.workspace))
        )
        return result.scalar_one_or_none()

    async def create(self, agent: AgentModel) -> AgentModel:
        self.session.add(agent)
        await self.session.flush()
        return agent

    async def delete(self, agent_id: str) -> bool:
        agent = await self.get(agent_id)
        if agent is None:
            return False
        await self.session.delete(agent)
        await self.session.flush()
        return True

    async def attach_workspace(self, agent: AgentModel) -> AgentModel:
        if agent.workspace is None:
            agent.workspace = await self.session.get(WorkspaceModel, agent.workspace_id)
        return agent
