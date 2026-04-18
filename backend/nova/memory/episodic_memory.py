"""Recent, decaying memory."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from nova.types import MemoryItem


class EpisodicMemory:
    """Stores recent events per agent with TTL semantics."""

    def __init__(self, ttl_hours: int) -> None:
        self.ttl = timedelta(hours=ttl_hours)
        self._events: defaultdict[str, deque[MemoryItem]] = defaultdict(lambda: deque(maxlen=500))

    async def append(self, item: MemoryItem) -> None:
        self._events[item.agent_id].appendleft(item)

    async def recent(self, agent_id: str, limit: int = 10) -> list[MemoryItem]:
        await self.prune()
        return list(self._events.get(agent_id, []))[:limit]

    async def prune(self) -> None:
        now = datetime.now(timezone.utc)
        for agent_id, items in list(self._events.items()):
            kept = deque(
                [item for item in items if item.expires_at is None or item.expires_at > now],
                maxlen=500,
            )
            self._events[agent_id] = kept
