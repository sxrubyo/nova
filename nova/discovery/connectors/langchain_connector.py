"""LangChain / LangServe connector."""

from __future__ import annotations

from nova.discovery.agent_manifest import AgentTask, ConnectionResult, DiscoveredAgent, HealthStatus, TaskResult
from nova.discovery.connectors.base_connector import BaseAgentConnector


class LangChainConnector(BaseAgentConnector):
    """Call LangServe-style endpoints."""

    connector_name = "langchain"

    def __init__(self, config: dict[str, object] | None = None) -> None:
        super().__init__(config)
        self.base_url = ""

    async def connect(self, agent: DiscoveredAgent) -> ConnectionResult:
        self.base_url = str(self.config.get("base_url") or agent.metadata.get("base_url") or f"http://127.0.0.1:{agent.port or (agent.ports[0] if agent.ports else 8000)}")
        health = await self.health_check(agent)
        return ConnectionResult(
            success=health.ok,
            agent_key=agent.agent_key,
            connection_type="rest_api" if health.ok else None,
            connector=self.connector_name,
            capabilities=dict(agent.capabilities or {}),
            metadata={"base_url": self.base_url},
            error=None if health.ok else health.detail,
        )

    async def health_check(self, _: DiscoveredAgent) -> HealthStatus:
        for path in ["/health", "/", "/docs"]:
            try:
                response = await self._http_get(f"{self.base_url}{path}", timeout=4)
                if response.status_code < 500:
                    return HealthStatus(ok=True, status="online", detail=f"{self.base_url}{path}")
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
        return HealthStatus(ok=False, status="offline", detail=locals().get("last_error", "LangChain endpoint unavailable"))

    async def get_status(self, agent: DiscoveredAgent) -> dict[str, object]:
        health = await self.health_check(agent)
        return {"connector": self.connector_name, "base_url": self.base_url, "health": health.status}

    async def send_task(self, _: DiscoveredAgent, task: AgentTask) -> TaskResult:
        path = str(task.payload.get("invoke_path") or "/invoke")
        response = await self._http_post(
            f"{self.base_url}{path}",
            json_body={"input": task.payload.get("input", {"prompt": task.prompt}), "config": task.payload.get("config", {})},
            timeout=float(task.timeout or 60),
        )
        return TaskResult(
            success=response.status_code < 400,
            output=response.json() if "application/json" in response.headers.get("content-type", "") else response.text,
            status_code=response.status_code,
        )
