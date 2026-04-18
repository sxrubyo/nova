"""Memory engine orchestration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from nova.config import NovaConfig
from nova.memory.core_memory import CoreMemory
from nova.memory.episodic_memory import EpisodicMemory
from nova.memory.working_memory import WorkingMemory
from nova.storage.database import session_scope
from nova.storage.models import MemoryModel
from nova.types import MemoryItem, MemoryType
from nova.utils.crypto import generate_id


class MemoryEngine:
    """Combines core, episodic, and working memory."""

    def __init__(self, config: NovaConfig) -> None:
        self.config = config
        self.core_memory = CoreMemory()
        self.episodic_memory = EpisodicMemory(ttl_hours=config.episodic_ttl_hours)
        self.working_memory = WorkingMemory()

    async def get_recent(self, agent_id: str, limit: int = 10) -> list[dict[str, object]]:
        items = await self.episodic_memory.recent(agent_id, limit)
        return [item.value for item in items]

    async def store(
        self,
        agent_id: str,
        event_type: str,
        data: dict[str, object],
        importance: int,
        workspace_id: str | None = None,
    ) -> MemoryItem:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self.config.episodic_ttl_hours if importance < 10 else 24 * 365)
        item = MemoryItem(
            id=generate_id("mem"),
            agent_id=agent_id,
            workspace_id=workspace_id or "unknown",
            memory_type=MemoryType.EPISODIC,
            key=event_type,
            value=data,
            importance=importance,
            created_at=now,
            expires_at=expires_at,
        )
        await self.episodic_memory.append(item)
        async with session_scope() as session:
            session.add(
                MemoryModel(
                    id=item.id,
                    agent_id=item.agent_id,
                    workspace_id=item.workspace_id,
                    memory_type=item.memory_type.value,
                    key=item.key,
                    value=item.value,
                    importance=item.importance,
                    expires_at=item.expires_at,
                )
            )
        return item

    async def load_persistent(self, agent_id: str, limit: int = 100) -> list[MemoryItem]:
        async with session_scope() as session:
            result = await session.execute(
                select(MemoryModel)
                .where(MemoryModel.agent_id == agent_id)
                .order_by(MemoryModel.importance.desc(), MemoryModel.created_at.desc())
                .limit(limit)
            )
            items = []
            for row in result.scalars().all():
                items.append(
                    MemoryItem(
                        id=row.id,
                        agent_id=row.agent_id,
                        workspace_id=row.workspace_id,
                        memory_type=MemoryType(row.memory_type),
                        key=row.key,
                        value=dict(row.value or {}),
                        importance=row.importance,
                        created_at=row.created_at,
                        expires_at=row.expires_at,
                    )
                )
            return items

    async def prune(self) -> None:
        await self.episodic_memory.prune()
        async with session_scope() as session:
            await session.execute(
                delete(MemoryModel).where(
                    MemoryModel.expires_at.is_not(None),
                    MemoryModel.expires_at < datetime.now(timezone.utc),
                )
            )
