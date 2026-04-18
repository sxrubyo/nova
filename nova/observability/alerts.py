"""Simple alert collector used by anomaly and health monitoring."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any


class AlertManager:
    """Stores recent alerts in memory for fast access."""

    def __init__(self, limit: int = 200, event_bus: Any | None = None) -> None:
        self._alerts: deque[dict[str, Any]] = deque(maxlen=limit)
        self._event_bus = event_bus

    async def emit(self, category: str, message: str, metadata: dict[str, Any] | None = None) -> None:
        """Store an alert entry."""

        event = {
            "category": category,
            "message": message,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._alerts.appendleft(event)
        if self._event_bus is not None:
            await self._event_bus.publish(
                "anomaly_detected",
                {
                    "type": category,
                    "severity": (metadata or {}).get("severity", "info"),
                    "detail": message,
                    "metadata": metadata or {},
                },
            )

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the most recent alerts."""

        return list(self._alerts)[:limit]
