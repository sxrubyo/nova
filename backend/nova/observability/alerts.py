"""Simple alert collector used by anomaly and health monitoring."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any


class AlertManager:
    """Stores recent alerts in memory for fast access."""

    def __init__(self, limit: int = 200) -> None:
        self._alerts: deque[dict[str, Any]] = deque(maxlen=limit)

    async def emit(self, category: str, message: str, metadata: dict[str, Any] | None = None) -> None:
        """Store an alert entry."""

        self._alerts.appendleft(
            {
                "category": category,
                "message": message,
                "metadata": metadata or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the most recent alerts."""

        return list(self._alerts)[:limit]
