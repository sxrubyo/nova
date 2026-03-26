"""Background health checks for providers."""

from __future__ import annotations

import asyncio

from nova.observability.alerts import AlertManager
from nova.observability.logger import get_logger


class ProviderHealthChecker:
    """Periodically refresh provider health state."""

    def __init__(self, providers: list[object], alerts: AlertManager, interval_seconds: int = 30) -> None:
        self.providers = providers
        self.alerts = alerts
        self.interval_seconds = interval_seconds
        self.logger = get_logger("nova.gateway.health")
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="nova-provider-health")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _run(self) -> None:
        while not self._stop.is_set():
            await self.check_once()
            await asyncio.sleep(self.interval_seconds)

    async def check_once(self) -> None:
        online_count = 0
        for provider in self.providers:
            is_healthy = await provider.health_check()
            if is_healthy:
                online_count += 1
        if online_count == 0:
            await self.alerts.emit("providers_offline", "all configured providers are offline or degraded")


import contextlib  # noqa: E402
