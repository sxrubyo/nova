"""API tests for Gmail duplicate protection routes."""

from __future__ import annotations

import pytest

from tests.conftest import update_workspace


@pytest.mark.asyncio
async def test_gmail_duplicate_check_uses_recent_allowed_send_email(api_client, workspace, agent) -> None:
    await update_workspace(workspace.id, rules={"can_do": ["send_email"], "cannot_do": []})

    evaluate = await api_client.post(
        "/api/evaluate",
        headers={"x-api-key": workspace.api_key, "x-workspace-id": workspace.id},
        json={
            "agent_id": agent.id,
            "action": "send_email",
            "payload": {
                "recipient": "ops@example.com",
                "subject": "Weekly Newsletter",
                "body": "hello",
            },
        },
    )
    assert evaluate.status_code == 200

    duplicate = await api_client.get(
        "/api/gmail/check-duplicate",
        headers={"x-api-key": workspace.api_key},
        params={
            "recipient": "ops@example.com",
            "subject": "Weekly Newsletter",
            "timeframe_hours": 24,
        },
    )
    assert duplicate.status_code == 200
    payload = duplicate.json()
    assert payload["is_duplicate"] is True
    assert payload["recipient"] == "ops@example.com"
    assert payload["subject"] == "Weekly Newsletter"
    assert payload["ledger_hash"]


@pytest.mark.asyncio
async def test_gmail_duplicate_check_returns_false_when_no_match(api_client, workspace) -> None:
    response = await api_client.get(
        "/api/gmail/check-duplicate",
        headers={"x-api-key": workspace.api_key},
        params={
            "recipient": "nobody@example.com",
            "subject": "No Match",
            "timeframe_hours": 24,
        },
    )
    assert response.status_code == 200
    assert response.json()["is_duplicate"] is False
