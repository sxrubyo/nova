"""Discovery governance regressions."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from nova.discovery.agent_manifest import AgentTask, ConnectionResult, DiscoveredAgent, TaskResult
from nova.discovery.connector_factory import ConnectorFactory


class FakeConnector:
    connector_name = "fake-codex"

    def __init__(self) -> None:
        self.sent_tasks: list[AgentTask] = []

    async def connect(self, agent: DiscoveredAgent) -> ConnectionResult:
        return ConnectionResult(success=True, agent_key=agent.agent_key, connector=self.connector_name)

    async def disconnect(self, _: str) -> bool:
        return True

    async def get_status(self, _: DiscoveredAgent) -> dict[str, object]:
        return {"connector": self.connector_name}

    async def health_check(self, _: DiscoveredAgent) -> SimpleNamespace:
        return SimpleNamespace(ok=True, status="online", detail="")

    async def send_task(self, agent: DiscoveredAgent, task: AgentTask) -> TaskResult:
        self.sent_tasks.append(task)
        return TaskResult(success=True, output=f"ran {agent.agent_key}")

    async def pause(self, _: str) -> bool:
        return True

    async def resume(self, _: str) -> bool:
        return True

    async def get_logs(self, _: str, limit: int = 100) -> list[object]:
        return []


@pytest.mark.asyncio
async def test_discovered_codex_task_is_blocked_by_agent_permissions(kernel, workspace, monkeypatch) -> None:
    connector = FakeConnector()
    monkeypatch.setattr(ConnectorFactory, "create", lambda agent, config=None: connector)

    discovered = DiscoveredAgent(
        agent_key="codex_cli-local",
        fingerprint_key="codex_cli",
        name="Codex CLI",
        type="cli_agent",
        confidence=0.95,
        detection_method="binary",
        detection_methods=["binary", "config_file"],
        capabilities={
            "can_execute_code": True,
            "can_modify_files": True,
            "can_run_commands": True,
            "can_access_network": True,
        },
        binary_path="/usr/bin/codex",
        metadata={"source": "test"},
        risk_profile={"risk_factors": ["shell_access", "file_system_access"]},
    )
    kernel.discovery._cached_agents[discovered.agent_key] = discovered

    connect_result = await kernel.discovery.connect(
        agent_key=discovered.agent_key,
        workspace_id=workspace.id,
        config={},
        permissions={"cannot_do": ["rm -rf", "exfiltrate_secrets"]},
    )
    assert connect_result.success is True

    reconnect_result = await kernel.discovery.connect(
        agent_key=discovered.agent_key,
        workspace_id=workspace.id,
        config={},
    )
    assert reconnect_result.success is True
    assert "rm -rf" in reconnect_result.metadata["permissions"]["cannot_do"]

    result = await kernel.discovery.send_task(
        agent_key=discovered.agent_key,
        workspace_id=workspace.id,
        task=AgentTask(
            prompt="rm -rf /tmp/nova-demo",
            payload={"extra_args": ["--dangerously-skip-permissions"], "command": "rm -rf /tmp/nova-demo"},
            working_directory="/tmp",
        ),
    )

    assert result["success"] is False
    assert result["blocked"] is True
    assert result["evaluation"].decision.action.value == "BLOCK"
    assert connector.sent_tasks == []


@pytest.mark.asyncio
async def test_discovered_agent_tasks_receive_governance_overlay_before_delivery(kernel, workspace, monkeypatch) -> None:
    connector = FakeConnector()
    monkeypatch.setattr(ConnectorFactory, "create", lambda agent, config=None: connector)

    discovered = DiscoveredAgent(
        agent_key="codex_cli-governed",
        fingerprint_key="codex_cli",
        name="Codex CLI",
        type="cli_agent",
        confidence=0.95,
        detection_method="binary",
        detection_methods=["binary", "config_file"],
        capabilities={
            "can_execute_code": True,
            "can_modify_files": True,
            "can_run_commands": True,
            "can_access_network": True,
        },
        binary_path="/usr/bin/codex",
        metadata={"source": "test"},
        risk_profile={"risk_factors": ["shell_access", "file_system_access"]},
    )
    kernel.discovery._cached_agents[discovered.agent_key] = discovered

    connect_result = await kernel.discovery.connect(
        agent_key=discovered.agent_key,
        workspace_id=workspace.id,
        config={},
        permissions={"cannot_do": ["Nunca digas hola"], "can_do": ["Mantener tono profesional"]},
    )
    assert connect_result.success is True

    result = await kernel.discovery.send_task(
        agent_key=discovered.agent_key,
        workspace_id=workspace.id,
        task=AgentTask(prompt="Responde al cliente sobre horarios", payload={}),
    )

    assert result["success"] is True
    assert result["governance_overlay_applied"] is True
    sent_prompt = connector.sent_tasks[0].prompt
    assert "[Nova governance overlay]" in sent_prompt
    assert "silently rewrite it before returning the final answer" in sent_prompt
    assert "Nunca digas hola" in sent_prompt
    assert "Mantener tono profesional" in sent_prompt
