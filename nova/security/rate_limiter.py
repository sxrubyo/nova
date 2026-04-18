"""Token bucket rate limiter for API and bridge traffic."""

from __future__ import annotations

import time
from collections import defaultdict

from nova.platform import PLATFORM


class RateLimiter:
    """Per-key token bucket limiter."""

    def __init__(
        self,
        requests_per_minute: int | None = None,
        burst: int | None = None,
        *,
        rate_per_second: float | None = None,
    ) -> None:
        self.rate_per_second = rate_per_second or (
            (requests_per_minute / 60.0)
            if requests_per_minute is not None
            else (10.0 if PLATFORM.type == "termux" else 100.0)
        )
        self.burst = burst or (20 if PLATFORM.type == "termux" else 200)
        self._buckets: defaultdict[str, list[float]] = defaultdict(lambda: [float(self.burst), time.monotonic()])

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        tokens, last = self._buckets[key]
        tokens = min(float(self.burst), tokens + (now - last) * self.rate_per_second)
        if tokens < 1.0:
            self._buckets[key] = [tokens, now]
            return False
        self._buckets[key] = [tokens - 1.0, now]
        return True
