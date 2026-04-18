"""Background anomaly detection."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone

from nova.config import NovaConfig
from nova.observability.alerts import AlertManager
from nova.observability.logger import get_logger
from nova.types import AgentRecord, DecisionAction, WorkspaceRiskProfile


@dataclass(slots=True)
class AnomalyEvent:
    agent_id: str
    workspace_id: str
    action: str
    decision: str
    risk_score: int
    timestamp: datetime


class AnomalyDetector:
    """Evaluates agent behavior asynchronously to avoid blocking the pipeline."""

    def __init__(self, config: NovaConfig, alerts: AlertManager) -> None:
        self.config = config
        self.alerts = alerts
        self.logger = get_logger("nova.anomaly")
        self._queue: asyncio.Queue[AnomalyEvent] = asyncio.Queue()
        self._stop = asyncio.Event()
        self._worker_task: asyncio.Task[None] | None = None
        self._workspace_scores: defaultdict[str, deque[int]] = defaultdict(lambda: deque(maxlen=100))
        self._forbidden_access: defaultdict[str, deque[datetime]] = defaultdict(lambda: deque(maxlen=20))

    async def start(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker(), name="nova-anomaly-detector")

    async def stop(self) -> None:
        self._stop.set()
        if self._worker_task is not None:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task

    async def submit(self, event: AnomalyEvent) -> None:
        await self._queue.put(event)

    async def unusual_time(self, profile: WorkspaceRiskProfile) -> bool:
        now_hour = datetime.now(timezone.utc).hour
        return now_hour < profile.business_hours_start or now_hour >= profile.business_hours_end

    async def _worker(self) -> None:
        while not self._stop.is_set():
            event = await self._queue.get()
            try:
                await self._process(event)
            finally:
                self._queue.task_done()

    async def _process(self, event: AnomalyEvent) -> None:
        scores = self._workspace_scores[event.workspace_id]
        previous_avg = (sum(scores) / len(scores)) if scores else 0
        scores.append(event.risk_score)
        new_avg = sum(scores) / len(scores)
        if len(scores) >= 100 and new_avg > 60:
            await self.alerts.emit(
                "workspace_risk",
                f"workspace {event.workspace_id} rolling risk average is {new_avg:.1f}",
                {"workspace_id": event.workspace_id, "rolling_average": round(new_avg, 2)},
            )
        if scores and new_avg - previous_avg > 20:
            await self.alerts.emit(
                "risk_spike",
                f"workspace {event.workspace_id} risk average spiked by {new_avg - previous_avg:.1f}",
                {"workspace_id": event.workspace_id},
            )
        if event.decision == DecisionAction.BLOCK.value:
            attempts = self._forbidden_access[event.agent_id]
            attempts.append(event.timestamp)
            ten_minutes_ago = event.timestamp.timestamp() - 600
            while attempts and attempts[0].timestamp() < ten_minutes_ago:
                attempts.popleft()
            if len(attempts) >= 3:
                await self.alerts.emit(
                    "forbidden_access",
                    f"agent {event.agent_id} attempted blocked access {len(attempts)} times",
                    {"agent_id": event.agent_id, "attempts": len(attempts)},
                )


import contextlib  # noqa: E402  # imported late to keep the class block readable
