"""High-level discovery orchestration, connection management, and agent task dispatch."""

from __future__ import annotations

import asyncio
import copy
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from nova.discovery.agent_manifest import AgentTask, ConnectionResult, DiscoveredAgent, TaskResult
from nova.discovery.connector_factory import ConnectorFactory
from nova.discovery.fingerprints import AGENT_FINGERPRINTS
from nova.discovery.scanner import SystemScanner
from nova.discovery.watcher import AgentWatcher
from nova.realtime.event_bus import RuntimeEventBus
from nova.types import DecisionAction, EvaluationRequest


class DiscoveryEngine:
    """Own the discovery cache, connector lifecycle, and task execution bridge."""

    def __init__(
        self,
        *,
        kernel: Any,
        event_bus: RuntimeEventBus,
        scanner: SystemScanner | None = None,
        scan_ttl_seconds: int = 60,
        watch_interval_seconds: int = 60,
    ) -> None:
        self.kernel = kernel
        self.event_bus = event_bus
        self.scanner = scanner or SystemScanner()
        self.scan_ttl_seconds = scan_ttl_seconds
        self.watch_interval_seconds = watch_interval_seconds
        self.last_scan_at: datetime | None = None
        self.last_scan_duration_ms: float | None = None
        self._scan_lock = asyncio.Lock()
        self._cached_agents: dict[str, DiscoveredAgent] = {}
        self._connections: dict[str, dict[str, Any]] = {}
        self._watcher = AgentWatcher(self.scanner, interval=watch_interval_seconds, event_handler=self._handle_watcher_event)

    async def start(self) -> None:
        await self.scan(force=True)
        await self._watcher.start()

    async def stop(self) -> None:
        await self._watcher.stop()

    async def scan(self, *, force: bool = False) -> list[DiscoveredAgent]:
        async with self._scan_lock:
            if not force and self.last_scan_at and datetime.now(timezone.utc) - self.last_scan_at < timedelta(seconds=self.scan_ttl_seconds):
                return self.list_cached_agents()
            started = time.monotonic()
            agents = await self.scanner.full_scan()
            self._cached_agents = {agent.agent_key: agent for agent in agents}
            self.last_scan_at = datetime.now(timezone.utc)
            self.last_scan_duration_ms = (time.monotonic() - started) * 1000
            await self.event_bus.publish(
                "scan_completed",
                {
                    "agents_found": len(agents),
                    "duration_ms": round(self.last_scan_duration_ms, 2),
                    "last_scan_at": self.last_scan_at.isoformat(),
                },
            )
            return self.list_cached_agents()

    async def get_agent(self, agent_key: str, *, force_scan: bool = False) -> DiscoveredAgent | None:
        if force_scan or agent_key not in self._cached_agents:
            await self.scan(force=force_scan)
        agent = self._cached_agents.get(agent_key)
        if agent is None:
            return None
        return self._decorate(agent)

    def list_cached_agents(self) -> list[DiscoveredAgent]:
        return [self._decorate(agent) for agent in self._cached_agents.values()]

    async def connect(
        self,
        *,
        agent_key: str,
        workspace_id: str,
        config: dict[str, Any] | None = None,
    ) -> ConnectionResult:
        agent = await self.get_agent(agent_key)
        if agent is None:
            return ConnectionResult(success=False, agent_key=agent_key, error="agent not found")

        connector = ConnectorFactory.create(agent, config=config)
        result = await connector.connect(agent)
        if not result.success:
            return result

        record = await self.kernel.agent_registry.ensure(
            workspace_id=workspace_id,
            name=agent.name,
            model=self._default_model(agent),
            provider=self._provider(agent),
            description=f"Discovered via {', '.join(agent.detection_methods)}",
            capabilities=self._capability_list(agent),
            permissions=self._default_permissions(agent),
            metadata={
                **dict(agent.metadata or {}),
                "discovery": {
                    "agent_key": agent.agent_key,
                    "fingerprint_key": agent.fingerprint_key,
                    "confidence": agent.confidence,
                    "detection_methods": list(agent.detection_methods),
                    "version": agent.version,
                    "port": agent.port,
                    "pid": agent.pid,
                    "container_name": agent.container_name,
                },
                "connection": {
                    "connector": connector.connector_name,
                    "config": config or {},
                    "result": result.metadata,
                    "connected_at": datetime.now(timezone.utc).isoformat(),
                },
                "permissions": {
                    "can_do": self._default_permissions(agent),
                    "cannot_do": agent.risk_profile.get("risk_factors", []),
                },
            },
        )
        self._connections[agent.agent_key] = {
            "agent_id": record.id,
            "agent_key": agent.agent_key,
            "connector": connector,
            "connected_at": datetime.now(timezone.utc),
            "fingerprint_key": agent.fingerprint_key,
            "control_id": str(agent.pid or record.id),
        }
        await self.event_bus.publish(
            "agent_connected",
            {"agent_id": record.id, "agent_key": agent.agent_key, "name": agent.name, "type": agent.type},
        )
        result.agent_id = record.id
        result.agent_key = agent.agent_key
        return result

    async def disconnect(self, agent_key: str) -> bool:
        connection = self._connections.pop(agent_key, None)
        if connection is None:
            return False
        await connection["connector"].disconnect(connection["agent_id"])
        await self.kernel.agent_registry.update(connection["agent_id"], status="inactive")
        await self.event_bus.publish(
            "agent_disconnected",
            {"agent_id": connection["agent_id"], "agent_key": agent_key},
        )
        return True

    async def get_status(self, agent_key: str) -> dict[str, Any]:
        agent = await self.get_agent(agent_key)
        if agent is None:
            return {"error": "agent not found"}
        connection = self._connections.get(agent_key)
        if connection is None:
            return {
                "connected": False,
                "agent_key": agent.agent_key,
                "status": agent.status,
                "is_running": agent.is_running,
                "is_healthy": agent.is_healthy,
                "detection_methods": agent.detection_methods,
            }
        connector_status = await connection["connector"].get_status(agent)
        health = await connection["connector"].health_check(agent)
        return {
            "connected": True,
            "agent_id": connection["agent_id"],
            "agent_key": agent.agent_key,
            "connector": connection["connector"].connector_name,
            "health": asdict(health),
            "runtime": connector_status,
        }

    async def send_task(self, *, agent_key: str, workspace_id: str, task: AgentTask) -> dict[str, Any]:
        agent = await self.get_agent(agent_key)
        if agent is None:
            return {"success": False, "error": "agent not found"}
        connection = self._connections.get(agent_key)
        if connection is None:
            connect_result = await self.connect(agent_key=agent_key, workspace_id=workspace_id, config={})
            if not connect_result.success:
                return {"success": False, "error": connect_result.error or "unable to connect"}
            connection = self._connections.get(agent_key)
        assert connection is not None

        evaluation = await self.kernel.evaluate(
            EvaluationRequest(
                agent_id=connection["agent_id"],
                workspace_id=workspace_id,
                action=f"{agent.name} cli command",
                payload={
                    "prompt": task.prompt,
                    "model": task.model,
                    "agent_key": agent.agent_key,
                    "connector": connection["connector"].connector_name,
                    "command": task.prompt,
                    **dict(task.payload or {}),
                },
                source="discovery",
            )
        )
        if evaluation.decision.action != DecisionAction.ALLOW:
            return {
                "success": False,
                "blocked": True,
                "evaluation": evaluation,
                "error": f"Nova blocked task with decision {evaluation.decision.action.value}",
            }

        result = await connection["connector"].send_task(agent, task)
        await self.event_bus.publish(
            "task_completed",
            {
                "agent_id": connection["agent_id"],
                "agent_key": agent.agent_key,
                "success": result.success,
                "duration_ms": result.duration_ms,
            },
        )
        return {"success": result.success, "evaluation": evaluation, "task_result": result}

    async def get_logs(self, agent_key: str, *, limit: int = 100) -> list[dict[str, Any]]:
        connection = self._connections.get(agent_key)
        if connection is None:
            return []
        return [asdict(item) for item in await connection["connector"].get_logs(connection["agent_id"], limit=limit)]

    async def pause(self, agent_key: str) -> bool:
        connection = self._connections.get(agent_key)
        if connection is None:
            return False
        return await connection["connector"].pause(connection.get("control_id", connection["agent_id"]))

    async def resume(self, agent_key: str) -> bool:
        connection = self._connections.get(agent_key)
        if connection is None:
            return False
        return await connection["connector"].resume(connection.get("control_id", connection["agent_id"]))

    async def create_managed_agent(
        self,
        *,
        workspace_id: str,
        name: str,
        agent_type: str,
        model: str,
        config: dict[str, Any],
        permissions: dict[str, list[str]] | None = None,
        risk_thresholds: dict[str, int] | None = None,
        quota: dict[str, int] | None = None,
    ) -> tuple[Any, ConnectionResult | None]:
        fingerprint_key = ConnectorFactory.fingerprint_for_type(agent_type)
        fingerprint = AGENT_FINGERPRINTS.get(fingerprint_key, {})
        record = await self.kernel.agent_registry.create(
            workspace_id=workspace_id,
            name=name,
            model=model,
            provider=self._provider_from_type(agent_type),
            description=f"Managed {agent_type} agent",
            capabilities=self._capability_list_from_fingerprint(fingerprint),
            permissions=list((permissions or {}).get("can_do", [])),
            metadata={
                "agent_type": agent_type,
                "connection": config,
                "permissions": permissions or {"can_do": [], "cannot_do": []},
                "risk_thresholds": risk_thresholds or {},
                "quota": quota or {},
            },
        )
        if fingerprint_key == "custom":
            pseudo_agent = DiscoveredAgent(
                agent_key=record.id,
                fingerprint_key="custom",
                name=name,
                type=agent_type,
                confidence=1.0,
                detection_method="manual",
                detection_methods=["manual"],
                capabilities={},
                metadata={"connection": config},
                risk_profile={},
            )
        else:
            pseudo_agent = DiscoveredAgent(
                agent_key=record.id,
                fingerprint_key=fingerprint_key,
                name=name,
                type=fingerprint.get("type", agent_type),
                confidence=1.0,
                detection_method="manual",
                detection_methods=["manual"],
                capabilities=dict(fingerprint.get("capabilities", {})),
                metadata={"connection": config, "permissions": permissions or {}, "risk_thresholds": risk_thresholds or {}, "quota": quota or {}},
                risk_profile=dict(fingerprint.get("risk_profile", {})),
            )
        connector = ConnectorFactory.create_for_type(agent_type, config=config)
        connection_result = await connector.connect(pseudo_agent)
        if connection_result.success:
            self._connections[pseudo_agent.agent_key] = {
                "agent_id": record.id,
                "agent_key": pseudo_agent.agent_key,
                "connector": connector,
                "connected_at": datetime.now(timezone.utc),
                "fingerprint_key": fingerprint_key,
                "control_id": str(config.get("pid") or record.id),
            }
        return record, connection_result

    async def _handle_watcher_event(self, event_type: str, agent: DiscoveredAgent) -> None:
        self._cached_agents[agent.agent_key] = agent
        await self.event_bus.publish(
            event_type,
            {
                "agent_key": agent.agent_key,
                "fingerprint_key": agent.fingerprint_key,
                "name": agent.name,
                "type": agent.type,
                "confidence": agent.confidence,
                "status": agent.status,
                "port": agent.port,
                "pid": agent.pid,
            },
        )

    def _decorate(self, agent: DiscoveredAgent) -> DiscoveredAgent:
        decorated = copy.deepcopy(agent)
        connection = self._connections.get(agent.agent_key)
        decorated.metadata = {
            **dict(decorated.metadata or {}),
            "connected": connection is not None,
            "connected_agent_id": connection["agent_id"] if connection else None,
            "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
        }
        return decorated

    def _default_model(self, agent: DiscoveredAgent) -> str:
        models = agent.capabilities.get("supported_models") or []
        if models:
            return str(models[0])
        return "gpt-4o-mini"

    def _provider(self, agent: DiscoveredAgent) -> str:
        if agent.fingerprint_key == "codex_cli":
            return "openai"
        if agent.fingerprint_key == "n8n":
            return "n8n"
        return agent.fingerprint_key

    def _provider_from_type(self, agent_type: str) -> str:
        return {"codex": "openai", "n8n": "n8n"}.get(agent_type, agent_type)

    def _capability_list(self, agent: DiscoveredAgent) -> list[str]:
        return self._capability_list_from_fingerprint({"capabilities": agent.capabilities})

    def _capability_list_from_fingerprint(self, fingerprint: dict[str, Any]) -> list[str]:
        capabilities = []
        for key, value in fingerprint.get("capabilities", {}).items():
            if value is True:
                capabilities.append(key)
        return capabilities

    def _default_permissions(self, agent: DiscoveredAgent) -> list[str]:
        capabilities = []
        capability_map = {
            "can_execute_code": "execute_code",
            "can_modify_files": "write_files",
            "can_run_commands": "run_commands",
            "can_access_network": "call_external_api",
            "has_api": "call_agent_api",
        }
        for key, permission in capability_map.items():
            if agent.capabilities.get(key):
                capabilities.append(permission)
        return capabilities
