"""Custom connector supporting REST, websocket, subprocess, Python, and Docker modes."""

from __future__ import annotations

import json
import sys
from typing import Any

import websockets

from nova.discovery.agent_manifest import AgentTask, ConnectionResult, DiscoveredAgent, HealthStatus, TaskResult
from nova.discovery.connectors.base_connector import BaseAgentConnector


class CustomAgentConnector(BaseAgentConnector):
    """Configurable bridge for user-defined agent integrations."""

    connector_name = "custom"

    async def connect(self, agent: DiscoveredAgent) -> ConnectionResult:
        config = self._resolved_config(agent)
        health = await self.health_check(agent)
        return ConnectionResult(
            success=health.ok,
            agent_key=agent.agent_key,
            connection_type=str(config.get("type") or "custom"),
            connector=self.connector_name,
            capabilities=dict(agent.capabilities or {}),
            metadata={"config_type": config.get("type")},
            error=None if health.ok else health.detail,
        )

    async def health_check(self, agent: DiscoveredAgent) -> HealthStatus:
        config = self._resolved_config(agent)
        config_type = str(config.get("type") or "rest_api")
        if config_type == "rest_api":
            base_url = str(config.get("base_url") or "")
            health_path = str(config.get("health_endpoint") or "/health")
            try:
                response = await self._http_get(f"{base_url}{health_path}", headers=config.get("headers"))
            except Exception as exc:  # noqa: BLE001
                return HealthStatus(ok=False, status="offline", detail=str(exc))
            return HealthStatus(ok=response.status_code < 500, status="online" if response.status_code < 500 else "degraded", detail=f"{base_url}{health_path}")
        if config_type == "subprocess":
            command = [str(config.get("command"))]
            result = await self._run_subprocess(command, cwd=config.get("cwd"), timeout=10)
            return HealthStatus(ok=result.success, status="online" if result.success else "offline", detail=result.output or result.error or "")
        if config_type == "python_module":
            module_name = str(config.get("module") or config.get("python_module") or "")
            available = self._import_module(module_name) if module_name else False
            return HealthStatus(ok=available, status="online" if available else "offline", detail=module_name or "module not provided")
        if config_type == "docker":
            container = str(config.get("container_name") or "")
            result = await self._run_subprocess(["docker", "inspect", container], timeout=10)
            return HealthStatus(ok=result.success, status="online" if result.success else "offline", detail=result.output or result.error or "")
        if config_type == "websocket":
            url = str(config.get("url") or config.get("websocket_url") or "")
            try:
                async with websockets.connect(url):
                    return HealthStatus(ok=True, status="online", detail=url)
            except Exception as exc:  # noqa: BLE001
                return HealthStatus(ok=False, status="offline", detail=str(exc))
        return HealthStatus(ok=False, status="offline", detail=f"unsupported custom connector type: {config_type}")

    async def get_status(self, agent: DiscoveredAgent) -> dict[str, object]:
        health = await self.health_check(agent)
        return {"connector": self.connector_name, "health": health.status, "detail": health.detail, "config": self._resolved_config(agent)}

    async def send_task(self, agent: DiscoveredAgent, task: AgentTask) -> TaskResult:
        config = self._resolved_config(agent)
        config_type = str(config.get("type") or "rest_api")
        if config_type == "rest_api":
            base_url = str(config.get("base_url") or "")
            execute_endpoint = str(config.get("execute_endpoint") or config.get("run_endpoint") or "/run")
            response = await self._http_post(
                f"{base_url}{execute_endpoint}",
                json_body={"prompt": task.prompt, "model": task.model, "payload": task.payload},
                headers=config.get("headers"),
                timeout=float(task.timeout or 60),
            )
            return TaskResult(
                success=response.status_code < 400,
                output=response.json() if "application/json" in response.headers.get("content-type", "") else response.text,
                status_code=response.status_code,
            )
        if config_type == "subprocess":
            command = [str(config.get("command"))] + [str(item) for item in config.get("args", [])] + [task.prompt]
            return await self._run_subprocess(command, cwd=config.get("cwd"), timeout=task.timeout or 300)
        if config_type == "python_module":
            module_name = str(config.get("module") or config.get("python_module") or "")
            script = (
                "import importlib, json, sys;"
                "mod = importlib.import_module(sys.argv[1]);"
                "handler = getattr(mod, 'run', None) or getattr(mod, 'main', None);"
                "result = handler(sys.argv[2]) if callable(handler) else {'error': 'missing run/main handler'};"
                "print(json.dumps(result, default=str))"
            )
            return await self._run_subprocess([sys.executable, "-c", script, module_name, task.prompt], timeout=task.timeout or 300)
        if config_type == "docker":
            container = str(config.get("container_name") or "")
            exec_command = str(config.get("exec_command") or task.prompt)
            return await self._run_subprocess(["docker", "exec", container, "sh", "-lc", exec_command], timeout=task.timeout or 300)
        if config_type == "websocket":
            url = str(config.get("url") or config.get("websocket_url") or "")
            try:
                async with websockets.connect(url) as websocket:
                    await websocket.send(json.dumps({"prompt": task.prompt, "model": task.model, "payload": task.payload}, default=str))
                    response = await websocket.recv()
            except Exception as exc:  # noqa: BLE001
                return TaskResult(success=False, error=str(exc))
            return TaskResult(success=True, output=response)
        return TaskResult(success=False, error=f"unsupported custom connector type: {config_type}")

    def _resolved_config(self, agent: DiscoveredAgent) -> dict[str, Any]:
        metadata_config = agent.metadata.get("custom_config") or agent.metadata.get("connection") or {}
        return {**metadata_config, **self.config}
