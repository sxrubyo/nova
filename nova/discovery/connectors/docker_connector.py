"""Docker-backed connector."""

from __future__ import annotations

from nova.discovery.agent_manifest import AgentTask, ConnectionResult, DiscoveredAgent, HealthStatus, TaskResult
from nova.discovery.connectors.base_connector import BaseAgentConnector


class DockerConnector(BaseAgentConnector):
    """Execute tasks inside already-running containers."""

    connector_name = "docker"

    async def connect(self, agent: DiscoveredAgent) -> ConnectionResult:
        container = agent.container_name or agent.container_id
        if not container:
            return ConnectionResult(success=False, agent_key=agent.agent_key, error="container id is missing")
        status = await self.get_status(agent)
        return ConnectionResult(
            success=status.get("state") == "running",
            agent_key=agent.agent_key,
            connection_type="docker_api",
            connector=self.connector_name,
            capabilities=dict(agent.capabilities or {}),
            metadata=status,
            error=None if status.get("state") == "running" else "container is not running",
        )

    async def health_check(self, agent: DiscoveredAgent) -> HealthStatus:
        status = await self.get_status(agent)
        running = status.get("state") == "running"
        return HealthStatus(ok=running, status="online" if running else "offline", detail=str(status.get("state") or "unknown"))

    async def get_status(self, agent: DiscoveredAgent) -> dict[str, object]:
        container = agent.container_name or agent.container_id
        if not container:
            return {"state": "missing"}
        payload = await self._json_command(["docker", "inspect", container], timeout=15)
        if isinstance(payload, list) and payload:
            first = payload[0]
            return {
                "state": str((first.get("State") or {}).get("Status") or "unknown"),
                "health": ((first.get("State") or {}).get("Health") or {}).get("Status"),
                "image": (first.get("Config") or {}).get("Image"),
                "name": first.get("Name"),
            }
        return {"state": "unknown", "raw": payload}

    async def send_task(self, agent: DiscoveredAgent, task: AgentTask) -> TaskResult:
        container = agent.container_name or agent.container_id
        if not container:
            return TaskResult(success=False, error="container id is missing")
        command = str(task.payload.get("command") or task.prompt)
        return await self._run_subprocess(["docker", "exec", container, "sh", "-lc", command], timeout=task.timeout or 300)
