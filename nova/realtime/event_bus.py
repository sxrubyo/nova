"""In-memory runtime event bus used by realtime APIs and discovery watchers."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class RuntimeEvent:
    """Serializable event payload emitted by Nova subsystems."""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RuntimeEventBus:
    """Tiny async pub/sub with a recent event buffer."""

    def __init__(self, limit: int = 200) -> None:
        self._events: deque[RuntimeEvent] = deque(maxlen=limit)
        self._subscribers: set[asyncio.Queue[RuntimeEvent]] = set()

    async def publish(self, event_type: str, payload: dict[str, Any] | None = None) -> RuntimeEvent:
        event = RuntimeEvent(type=event_type, payload=payload or {})
        self._events.appendleft(event)
        stale: list[asyncio.Queue[RuntimeEvent]] = []
        for subscriber in self._subscribers:
            try:
                subscriber.put_nowait(event)
            except asyncio.QueueFull:
                stale.append(subscriber)
        for subscriber in stale:
            self._subscribers.discard(subscriber)
        return event

    def subscribe(self, max_queue_size: int = 100) -> asyncio.Queue[RuntimeEvent]:
        queue: asyncio.Queue[RuntimeEvent] = asyncio.Queue(maxsize=max_queue_size)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[RuntimeEvent]) -> None:
        self._subscribers.discard(queue)

    def recent(self, limit: int = 100) -> list[RuntimeEvent]:
        return list(self._events)[:limit]
