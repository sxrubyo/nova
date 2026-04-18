"""Process connector."""

from __future__ import annotations

import os
import signal

from nova.discovery.agent_manifest import AgentTask, ConnectionResult, DiscoveredAgent, HealthStatus, TaskResult
from nova.discovery.connectors.base_connector import BaseAgentConnector


class ProcessConnector(BaseAgentConnector):
    """Best-effort control of local long-running processes."""

    connector_name = "process"

    async def connect(self, agent: DiscoveredAgent) -> ConnectionResult:
        if not agent.pid:
            return ConnectionResult(success=False, agent_key=agent.agent_key, error="pid is missing")
        alive = await self.health_check(agent)
        return ConnectionResult(
            success=alive.ok,
            agent_key=agent.agent_key,
            connection_type="process_monitor",
            connector=self.connector_name,
            capabilities=dict(agent.capabilities or {}),
            metadata={"pid": agent.pid},
            error=None if alive.ok else alive.detail,
        )

    async def health_check(self, agent: DiscoveredAgent) -> HealthStatus:
        if not agent.pid:
            return HealthStatus(ok=False, status="offline", detail="pid is missing")
        try:
            os.kill(agent.pid, 0)
        except OSError as exc:
            return HealthStatus(ok=False, status="offline", detail=str(exc))
        return HealthStatus(ok=True, status="online", detail=f"pid {agent.pid} is alive")

    async def get_status(self, agent: DiscoveredAgent) -> dict[str, object]:
        health = await self.health_check(agent)
        return {"connector": self.connector_name, "pid": agent.pid, "health": health.status, "process_info": agent.process_info}

    async def send_task(self, agent: DiscoveredAgent, task: AgentTask) -> TaskResult:
        command = str(task.payload.get("command") or "")
        if not command:
            return TaskResult(success=False, error="generic system processes need payload.command for task execution")
        return await self._run_subprocess(["sh", "-lc", command], cwd=task.working_directory, timeout=task.timeout or 300)

    async def pause(self, agent_id: str) -> bool:
        try:
            os.kill(int(agent_id), signal.SIGSTOP)
            return True
        except Exception:  # noqa: BLE001
            return False

    async def resume(self, agent_id: str) -> bool:
        try:
            os.kill(int(agent_id), signal.SIGCONT)
            return True
        except Exception:  # noqa: BLE001
            return False
