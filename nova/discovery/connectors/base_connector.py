"""Base connector contract."""

from __future__ import annotations

import abc
import asyncio
import importlib
import json
import subprocess
import time
from typing import Any

import httpx

from nova.discovery.agent_manifest import AgentLogEntry, AgentTask, ConnectionResult, DiscoveredAgent, HealthStatus, TaskResult


class BaseAgentConnector(abc.ABC):
    """Interface every discovery connector implements."""

    connector_name = "base"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    @abc.abstractmethod
    async def connect(self, agent: DiscoveredAgent) -> ConnectionResult:
        """Establish a connection to the discovered agent."""

    async def disconnect(self, _: str) -> bool:
        return True

    @abc.abstractmethod
    async def health_check(self, agent: DiscoveredAgent) -> HealthStatus:
        """Check whether the target is alive and reachable."""

    @abc.abstractmethod
    async def get_status(self, agent: DiscoveredAgent) -> dict[str, Any]:
        """Return detailed runtime status."""

    @abc.abstractmethod
    async def send_task(self, agent: DiscoveredAgent, task: AgentTask) -> TaskResult:
        """Execute a task through the target agent."""

    async def pause(self, _: str) -> bool:
        return False

    async def resume(self, _: str) -> bool:
        return False

    async def get_logs(self, _: str, limit: int = 100) -> list[AgentLogEntry]:
        return [
            AgentLogEntry(
                timestamp=str(int(time.time())),
                level="info",
                message=f"{self.connector_name} does not expose structured logs",
                metadata={"limit": limit},
            )
        ]

    async def get_capabilities(self, agent: DiscoveredAgent) -> dict[str, Any]:
        return dict(agent.capabilities or {})

    async def _http_get(self, url: str, *, headers: dict[str, str] | None = None, auth: Any = None, timeout: float = 5.0) -> httpx.Response:
        async with httpx.AsyncClient(timeout=timeout, headers=headers, auth=auth) as client:
            return await client.get(url)

    async def _http_post(
        self,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        auth: Any = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=timeout, headers=headers, auth=auth) as client:
            return await client.post(url, json=json_body)

    async def _run_subprocess(self, command: list[str], *, cwd: str | None = None, timeout: int = 300) -> TaskResult:
        started = time.monotonic()
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except FileNotFoundError as exc:
            return TaskResult(success=False, error=str(exc), duration_ms=(time.monotonic() - started) * 1000)
        except asyncio.TimeoutError:
            return TaskResult(success=False, error="task execution timed out", duration_ms=(time.monotonic() - started) * 1000)

        return TaskResult(
            success=process.returncode == 0,
            output=stdout.decode("utf-8", errors="replace").strip(),
            error=stderr.decode("utf-8", errors="replace").strip() or None,
            exit_code=process.returncode,
            duration_ms=(time.monotonic() - started) * 1000,
        )

    def _import_module(self, module_name: str) -> bool:
        try:
            importlib.import_module(module_name)
            return True
        except Exception:  # noqa: BLE001
            return False

    async def _json_command(self, command: list[str], timeout: int = 20) -> Any:
        completed = await asyncio.to_thread(
            subprocess.run,
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        payload = (completed.stdout or completed.stderr or "").strip()
        if not payload:
            return {}
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {"raw": payload, "returncode": completed.returncode}
