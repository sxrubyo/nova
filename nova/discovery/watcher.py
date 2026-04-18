"""Background watcher that keeps discovery state fresh."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from typing import Any

from nova.discovery.agent_manifest import DiscoveredAgent


class AgentWatcher:
    """Continuously scan the host and emit discovery changes."""

    def __init__(
        self,
        scanner: Any,
        *,
        interval: int = 60,
        event_handler: Callable[[str, DiscoveredAgent], Awaitable[None]] | None = None,
    ) -> None:
        self.scanner = scanner
        self.interval = interval
        self.event_handler = event_handler
        self.known_agents: dict[str, DiscoveredAgent] = {}
        self._running = False
        self._task: asyncio.Task[Any] | None = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._run(), name="nova-agent-watcher")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _run(self) -> None:
        await self._scan_and_diff()
        while self._running:
            await asyncio.sleep(self.interval)
            await self._scan_and_diff()

    async def _scan_and_diff(self) -> None:
        current = {agent.agent_key: agent for agent in await self.scanner.full_scan()}
        current_keys = set(current)
        known_keys = set(self.known_agents)

        for agent_key in current_keys - known_keys:
            await self._emit("agent_discovered", current[agent_key])

        for agent_key in known_keys - current_keys:
            await self._emit("agent_lost", self.known_agents[agent_key])

        for agent_key in current_keys & known_keys:
            current_agent = current[agent_key]
            previous_agent = self.known_agents[agent_key]
            if previous_agent.is_running != current_agent.is_running:
                await self._emit("agent_started" if current_agent.is_running else "agent_stopped", current_agent)
            if previous_agent.is_healthy != current_agent.is_healthy:
                await self._emit("agent_healthy" if current_agent.is_healthy else "agent_unhealthy", current_agent)

        self.known_agents = current

    async def _emit(self, event_type: str, agent: DiscoveredAgent) -> None:
        if self.event_handler is not None:
            await self.event_handler(event_type, agent)
