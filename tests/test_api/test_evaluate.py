"""API evaluate endpoint tests."""

from __future__ import annotations

import pytest

from tests.conftest import update_workspace


@pytest.mark.asyncio
async def test_evaluate_endpoint(api_client, workspace, agent) -> None:
    await update_workspace(workspace.id, rules={"can_do": ["send_email"], "cannot_do": []})
    response = await api_client.post(
        "/api/evaluate",
        headers={"x-api-key": workspace.api_key, "x-workspace-id": workspace.id},
        json={"agent_id": agent.id, "action": "send_email", "payload": {"to": "ops@example.com", "body": "hello"}},
    )
    assert response.status_code == 200
    assert response.json()["decision"]["action"] == "ALLOW"
