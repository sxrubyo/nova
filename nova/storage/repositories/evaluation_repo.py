"""Evaluation persistence helpers."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nova.storage.models import EvaluationModel


class EvaluationRepository:
    """CRUD operations and analytics for evaluations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, evaluation: EvaluationModel) -> EvaluationModel:
        self.session.add(evaluation)
        await self.session.flush()
        return evaluation

    async def list_by_agent(self, agent_id: str, limit: int = 50) -> list[EvaluationModel]:
        result = await self.session.execute(
            select(EvaluationModel)
            .where(EvaluationModel.agent_id == agent_id)
            .order_by(desc(EvaluationModel.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_workspace(self, workspace_id: str, limit: int = 1000) -> list[EvaluationModel]:
        result = await self.session.execute(
            select(EvaluationModel)
            .where(EvaluationModel.workspace_id == workspace_id)
            .order_by(desc(EvaluationModel.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_workspace(self, workspace_id: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(EvaluationModel).where(EvaluationModel.workspace_id == workspace_id)
        )
        return int(result.scalar_one())

    async def count_since(self, agent_id: str, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(EvaluationModel)
            .where(EvaluationModel.agent_id == agent_id, EvaluationModel.created_at >= since)
        )
        return int(result.scalar_one())
