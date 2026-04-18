"""API discovery endpoint tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nova.discovery.agent_manifest import DiscoveredAgent


@pytest.mark.asyncio
async def test_discovery_scan_endpoint(api_client, workspace, kernel, monkeypatch) -> None:
    agent = DiscoveredAgent(
        agent_key="codex_cli-test",
        fingerprint_key="codex_cli",
        name="Codex CLI",
        type="cli_agent",
        confidence=0.95,
        detection_method="binary",
        detection_methods=["binary"],
        capabilities={"can_run_commands": True},
        risk_profile={"base_risk": 45},
    )

    async def fake_scan(*, force: bool = False):
        kernel.discovery.last_scan_at = datetime.now(timezone.utc)
        kernel.discovery.last_scan_duration_ms = 12.5
        return [agent]

    monkeypatch.setattr(kernel.discovery, "scan", fake_scan)

    response = await api_client.get("/api/discovery/scan", headers={"x-api-key": workspace.api_key})
    assert response.status_code == 200
    payload = response.json()
    assert payload["agents"][0]["name"] == "Codex CLI"
    assert isinstance(payload["duration_ms"], float)


@pytest.mark.asyncio
async def test_create_managed_agent_endpoint(api_client, workspace) -> None:
    response = await api_client.post(
        "/api/agents/create",
        headers={"x-api-key": workspace.api_key},
        json={
            "name": "custom-managed",
            "type": "custom",
            "model": "custom-runtime",
            "config": {
                "type": "subprocess",
                "command": "/bin/echo",
            },
            "permissions": {"can_do": ["call_agent_api"], "cannot_do": ["delete_production_db"]},
            "risk_thresholds": {"auto_allow": 25, "escalate": 55, "auto_block": 78},
            "quota": {"max_evaluations_per_day": 100, "max_tokens_per_request": 2000},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["agent"]["name"] == "custom-managed"
    assert payload["connection"]["success"] is True
