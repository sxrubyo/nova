"""API ledger endpoint tests."""

from __future__ import annotations

import pytest

from tests.conftest import update_workspace


@pytest.mark.asyncio
async def test_ledger_endpoints(api_client, workspace, agent) -> None:
    await update_workspace(workspace.id, rules={"can_do": ["send_email"], "cannot_do": []})
    evaluate = await api_client.post(
        "/api/evaluate",
        headers={"x-api-key": workspace.api_key, "x-workspace-id": workspace.id},
        json={"agent_id": agent.id, "action": "send_email", "payload": {"to": "ops@example.com", "body": "hello"}},
    )
    assert evaluate.status_code == 200

    listing = await api_client.get("/api/ledger", headers={"x-api-key": workspace.api_key})
    assert listing.status_code == 200
    assert len(listing.json()) >= 1

    verification = await api_client.get("/api/ledger/verify", headers={"x-api-key": workspace.api_key})
    assert verification.status_code == 200
    assert verification.json()["is_valid"] is True
