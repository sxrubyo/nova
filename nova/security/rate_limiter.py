"""Simple rate limiter for API and bridge traffic."""

from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    """Per-key sliding window rate limiter."""

    def __init__(self, requests_per_minute: int) -> None:
        self.requests_per_minute = requests_per_minute
        self._events: defaultdict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        events = self._events[key]
        events.append(now)
        while events and now - events[0] > 60:
            events.popleft()
        return len(events) <= self.requests_per_minute
