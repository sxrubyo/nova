"""n8n REST connector."""

from __future__ import annotations

import os
import socket
from urllib.parse import urlparse, urlunparse

import httpx

from nova.discovery.agent_manifest import AgentLogEntry, AgentTask, ConnectionResult, DiscoveredAgent, HealthStatus, TaskResult
from nova.discovery.connectors.base_connector import BaseAgentConnector


class N8NConnector(BaseAgentConnector):
    """Connect to n8n workflows via its REST API."""

    connector_name = "n8n"

    def __init__(self, config: dict[str, object] | None = None) -> None:
        super().__init__(config)
        self.base_url = ""
        self.auth: httpx.BasicAuth | None = None

    async def connect(self, agent: DiscoveredAgent) -> ConnectionResult:
        self.base_url = str(self.config.get("n8n_url") or agent.metadata.get("n8n_url") or f"http://127.0.0.1:{agent.port or 5678}")
        user = str(self.config.get("user") or os.getenv("N8N_BASIC_AUTH_USER") or "")
        password = str(self.config.get("password") or os.getenv("N8N_BASIC_AUTH_PASSWORD") or "")
        self.auth = httpx.BasicAuth(user, password) if user else None
        health = await self.health_check(agent)
        if not health.ok:
            return ConnectionResult(success=False, agent_key=agent.agent_key, connector=self.connector_name, error=health.detail)
        workflows = await self._list_workflows()
        return ConnectionResult(
            success=True,
            agent_key=agent.agent_key,
            connection_type="rest_api",
            connector=self.connector_name,
            capabilities=dict(agent.capabilities or {}),
            metadata={"base_url": self.base_url, "total_workflows": len(workflows)},
        )

    async def health_check(self, _: DiscoveredAgent) -> HealthStatus:
        for candidate_base_url in self._candidate_base_urls():
            for path in ["/healthz", "/rest/healthz", "/api/v1/workflows"]:
                try:
                    response = await self._http_get(f"{candidate_base_url}{path}", auth=self.auth, timeout=5)
                    if response.status_code < 500:
                        self.base_url = candidate_base_url
                        return HealthStatus(ok=True, status="online", detail=f"{candidate_base_url}{path}")
                except Exception as exc:  # noqa: BLE001
                    last_error = str(exc)
        return HealthStatus(ok=False, status="offline", detail=locals().get("last_error", "n8n is unreachable"))

    def _candidate_base_urls(self) -> list[str]:
        base_url = self.base_url.rstrip("/")
        candidates = [base_url]
        parsed = urlparse(base_url)
        if parsed.hostname not in {"127.0.0.1", "localhost", "0.0.0.0"}:
            return candidates

        gateway = self._default_gateway()
        if not gateway:
            return candidates

        netloc = gateway
        if parsed.port:
            netloc = f"{gateway}:{parsed.port}"
        rewritten = urlunparse(parsed._replace(netloc=netloc)).rstrip("/")
        if rewritten not in candidates:
            candidates.append(rewritten)
        return candidates

    def _default_gateway(self) -> str | None:
        try:
            with open("/proc/net/route", "r", encoding="utf-8") as route_file:
                for line in route_file.readlines()[1:]:
                    fields = line.strip().split()
                    if len(fields) < 3 or fields[1] != "00000000":
                        continue
                    return socket.inet_ntoa(bytes.fromhex(fields[2])[::-1])
        except Exception:  # noqa: BLE001
            return None
        return None

    async def get_status(self, agent: DiscoveredAgent) -> dict[str, object]:
        workflows = await self._list_workflows()
        executions = await self._list_executions(limit=20)
        return {
            "connector": self.connector_name,
            "is_running": agent.is_running,
            "base_url": self.base_url,
            "total_workflows": len(workflows),
            "active_workflows": len([item for item in workflows if item.get("active")]),
            "recent_executions": executions,
        }

    async def send_task(self, _: DiscoveredAgent, task: AgentTask) -> TaskResult:
        payload = task.payload or {}
        if payload.get("workflow_id"):
            response = await self._http_post(
                f"{self.base_url}/api/v1/workflows/{payload['workflow_id']}/execute",
                json_body=payload.get("input_data", {}),
                auth=self.auth,
                timeout=float(task.timeout or 60),
            )
        elif payload.get("webhook_path"):
            webhook_path = str(payload["webhook_path"]).lstrip("/")
            response = await self._http_post(
                f"{self.base_url}/webhook/{webhook_path}",
                json_body=payload.get("input_data", {}),
                auth=self.auth,
                timeout=float(task.timeout or 60),
            )
        else:
            return TaskResult(success=False, error="n8n tasks require workflow_id or webhook_path in payload")
        return TaskResult(
            success=response.status_code < 400,
            output=response.json() if "application/json" in response.headers.get("content-type", "") else response.text,
            status_code=response.status_code,
        )

    async def get_logs(self, _: str, limit: int = 100) -> list[AgentLogEntry]:
        executions = await self._list_executions(limit=limit)
        return [
            AgentLogEntry(
                timestamp=item.get("startedAt") or item.get("createdAt") or "",
                level="error" if item.get("status") == "error" else "info",
                message=f"{item.get('workflowData', {}).get('name', item.get('workflowId', 'workflow'))} - {item.get('status', 'unknown')}",
                metadata={"execution_id": item.get("id"), "workflow_id": item.get("workflowId")},
            )
            for item in executions
        ]

    async def _list_workflows(self) -> list[dict]:
        try:
            response = await self._http_get(f"{self.base_url}/api/v1/workflows", auth=self.auth, timeout=10)
            return response.json().get("data", [])
        except Exception:  # noqa: BLE001
            return []

    async def _list_executions(self, limit: int = 20) -> list[dict]:
        try:
            response = await self._http_get(f"{self.base_url}/api/v1/executions?limit={limit}", auth=self.auth, timeout=10)
            return response.json().get("data", [])
        except Exception:  # noqa: BLE001
            return []
