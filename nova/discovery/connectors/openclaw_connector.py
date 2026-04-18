"""OpenClaw and Open Interpreter connector."""

from __future__ import annotations

from nova.discovery.agent_manifest import AgentTask, ConnectionResult, DiscoveredAgent, HealthStatus, TaskResult
from nova.discovery.connectors.base_connector import BaseAgentConnector


class OpenClawConnector(BaseAgentConnector):
    """Use HTTP when available and fall back to the CLI when needed."""

    connector_name = "openclaw"

    def __init__(self, config: dict[str, object] | None = None) -> None:
        super().__init__(config)
        self.base_url = ""

    async def connect(self, agent: DiscoveredAgent) -> ConnectionResult:
        self.base_url = str(self.config.get("base_url") or agent.metadata.get("base_url") or f"http://127.0.0.1:{agent.port or (agent.ports[0] if agent.ports else 8080)}")
        health = await self.health_check(agent)
        if health.ok:
            return ConnectionResult(
                success=True,
                agent_key=agent.agent_key,
                connection_type="rest_api",
                connector=self.connector_name,
                capabilities=dict(agent.capabilities or {}),
                metadata={"base_url": self.base_url},
            )
        if agent.binary_path:
            return ConnectionResult(
                success=True,
                agent_key=agent.agent_key,
                connection_type="subprocess",
                connector=self.connector_name,
                capabilities=dict(agent.capabilities or {}),
                metadata={"binary_path": agent.binary_path},
            )
        return ConnectionResult(success=False, agent_key=agent.agent_key, connector=self.connector_name, error=health.detail)

    async def health_check(self, agent: DiscoveredAgent) -> HealthStatus:
        if self.base_url:
            for path in ["/health", "/api/health", "/"]:
                try:
                    response = await self._http_get(f"{self.base_url}{path}", timeout=4)
                    if response.status_code < 500:
                        return HealthStatus(ok=True, status="online", detail=f"{self.base_url}{path}")
                except Exception as exc:  # noqa: BLE001
                    last_error = str(exc)
        if agent.binary_path:
            result = await self._run_subprocess([agent.binary_path, "--help"], timeout=8)
            if result.success:
                return HealthStatus(ok=True, status="online", detail="openclaw CLI available")
        return HealthStatus(ok=False, status="offline", detail=locals().get("last_error", "OpenClaw is unreachable"))

    async def get_status(self, agent: DiscoveredAgent) -> dict[str, object]:
        health = await self.health_check(agent)
        return {
            "connector": self.connector_name,
            "base_url": self.base_url,
            "pid": agent.pid,
            "port": agent.port,
            "health": health.status,
            "detail": health.detail,
        }

    async def send_task(self, agent: DiscoveredAgent, task: AgentTask) -> TaskResult:
        payload = {**dict(task.payload or {}), "prompt": task.prompt, "model": task.model}
        if self.base_url:
            for endpoint in ["/api/run", "/run", "/tasks", "/chat"]:
                try:
                    response = await self._http_post(f"{self.base_url}{endpoint}", json_body=payload, timeout=float(task.timeout or 60))
                    if response.status_code < 500:
                        return TaskResult(
                            success=response.status_code < 400,
                            output=response.json() if "application/json" in response.headers.get("content-type", "") else response.text,
                            status_code=response.status_code,
                        )
                except Exception:  # noqa: BLE001
                    continue
        if agent.binary_path:
            command = [agent.binary_path, task.prompt]
            return await self._run_subprocess(command, cwd=task.working_directory, timeout=task.timeout or 300)
        return TaskResult(success=False, error="No OpenClaw execution path is available")
