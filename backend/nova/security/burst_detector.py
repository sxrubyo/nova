"""Burst activity detector."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from nova.types import BurstCheckResult


class BurstDetector:
    """Tracks per-agent request rate over a sliding time window."""

    def __init__(self) -> None:
        self._events: defaultdict[str, deque[float]] = defaultdict(deque)

    async def check(
        self,
        agent_id: str,
        window_seconds: int = 60,
        threshold: int = 50,
    ) -> BurstCheckResult:
        now = time.time()
        events = self._events[agent_id]
        events.append(now)
        while events and now - events[0] > window_seconds:
            events.popleft()
        return BurstCheckResult(
            is_burst=len(events) >= threshold,
            requests_in_window=len(events),
            window_seconds=window_seconds,
        )
