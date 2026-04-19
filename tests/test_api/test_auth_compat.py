"""Compatibility tests for auth/session and setup/status endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_auth_session_with_api_key(api_client, workspace) -> None:
    response = await api_client.get("/api/auth/session", headers={"x-api-key": workspace.api_key})

    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is True
    assert payload["workspace"]["id"] == workspace.id
    assert payload["workspace"]["api_key"] == workspace.api_key


@pytest.mark.asyncio
async def test_setup_status_exists(api_client) -> None:
    response = await api_client.get("/api/setup/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["needs_setup"] is False
    assert payload["recommended_login"] == "credentials"
