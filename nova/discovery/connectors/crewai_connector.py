"""CrewAI connector."""

from __future__ import annotations

import sys

from nova.discovery.agent_manifest import AgentTask, ConnectionResult, DiscoveredAgent, HealthStatus, TaskResult
from nova.discovery.connectors.base_connector import BaseAgentConnector


class CrewAIConnector(BaseAgentConnector):
    """Thin Python-wrapper connector for CrewAI runtimes."""

    connector_name = "crewai"

    async def connect(self, agent: DiscoveredAgent) -> ConnectionResult:
        available = self._import_module("crewai")
        return ConnectionResult(
            success=available,
            agent_key=agent.agent_key,
            connection_type="python_import" if available else None,
            connector=self.connector_name,
            capabilities=dict(agent.capabilities or {}),
            error=None if available else "CrewAI is not importable",
        )

    async def health_check(self, _: DiscoveredAgent) -> HealthStatus:
        available = self._import_module("crewai")
        return HealthStatus(ok=available, status="online" if available else "offline", detail="crewai import")

    async def get_status(self, agent: DiscoveredAgent) -> dict[str, object]:
        return {"connector": self.connector_name, "module_available": self._import_module("crewai"), "pid": agent.pid}

    async def send_task(self, agent: DiscoveredAgent, task: AgentTask) -> TaskResult:
        entrypoint = str(task.payload.get("entrypoint") or agent.metadata.get("entrypoint") or "")
        if not entrypoint:
            return TaskResult(success=False, error="CrewAI tasks require payload.entrypoint or agent metadata entrypoint")
        command = [sys.executable, entrypoint, task.prompt]
        return await self._run_subprocess(command, cwd=task.working_directory, timeout=task.timeout or 300)
