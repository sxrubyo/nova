"""In-memory metrics collection."""

from __future__ import annotations

from collections import defaultdict, deque
from statistics import mean
from typing import Any


class MetricsCollector:
    """Collects lightweight runtime metrics without external dependencies."""

    def __init__(self) -> None:
        self._evaluations: int = 0
        self._durations_ms: deque[float] = deque(maxlen=5000)
        self._risk_scores: deque[int] = deque(maxlen=5000)
        self._decisions: defaultdict[str, int] = defaultdict(int)
        self._provider_latency: defaultdict[str, deque[float]] = defaultdict(lambda: deque(maxlen=200))

    async def record_evaluation(
        self,
        duration_ms: float,
        risk_score: int,
        decision: str,
        provider: str | None,
    ) -> None:
        """Record a completed evaluation."""

        self._evaluations += 1
        self._durations_ms.append(duration_ms)
        self._risk_scores.append(risk_score)
        self._decisions[decision] += 1
        if provider:
            self._provider_latency[provider].append(duration_ms)

    def summary(self) -> dict[str, Any]:
        """Return aggregate metrics."""

        return {
            "evaluations": self._evaluations,
            "avg_duration_ms": round(mean(self._durations_ms), 2) if self._durations_ms else 0.0,
            "avg_risk_score": round(mean(self._risk_scores), 2) if self._risk_scores else 0.0,
            "decisions": dict(self._decisions),
        }

    def provider_snapshot(self) -> dict[str, float]:
        """Return average duration per provider."""

        return {
            provider: round(mean(latencies), 2)
            for provider, latencies in self._provider_latency.items()
            if latencies
        }
