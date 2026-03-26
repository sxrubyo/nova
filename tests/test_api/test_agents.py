"""API agent endpoint tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_agents_crud(api_client, workspace) -> None:
    create = await api_client.post(
        "/api/agents",
        headers={"x-api-key": workspace.api_key},
        json={"name": "api-agent", "model": "gpt-4o-mini", "provider": "openai", "description": "from api", "capabilities": []},
    )
    assert create.status_code == 200
    agent_id = create.json()["id"]

    listing = await api_client.get("/api/agents", headers={"x-api-key": workspace.api_key})
    assert listing.status_code == 200
    assert any(agent["id"] == agent_id for agent in listing.json())

    paused = await api_client.post(f"/api/agents/{agent_id}/pause", headers={"x-api-key": workspace.api_key})
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"
