"""Ledger persistence helpers."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from nova.storage.models import LedgerRecordModel


class LedgerRepository:
    """CRUD operations for immutable ledger records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def latest(self, workspace_id: str) -> LedgerRecordModel | None:
        result = await self.session.execute(
            select(LedgerRecordModel)
            .where(LedgerRecordModel.workspace_id == workspace_id)
            .order_by(desc(LedgerRecordModel.timestamp))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def add(self, record: LedgerRecordModel) -> LedgerRecordModel:
        self.session.add(record)
        await self.session.flush()
        return record

    async def get(self, action_id: str) -> LedgerRecordModel | None:
        return await self.session.get(LedgerRecordModel, action_id)

    async def get_by_eval_id(self, eval_id: str) -> LedgerRecordModel | None:
        result = await self.session.execute(
            select(LedgerRecordModel).where(LedgerRecordModel.eval_id == eval_id)
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: str, limit: int = 100) -> list[LedgerRecordModel]:
        result = await self.session.execute(
            select(LedgerRecordModel)
            .where(LedgerRecordModel.workspace_id == workspace_id)
            .order_by(desc(LedgerRecordModel.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def ordered_chain(self, workspace_id: str) -> list[LedgerRecordModel]:
        result = await self.session.execute(
            select(LedgerRecordModel)
            .where(LedgerRecordModel.workspace_id == workspace_id)
            .order_by(LedgerRecordModel.timestamp.asc())
        )
        return list(result.scalars().all())
