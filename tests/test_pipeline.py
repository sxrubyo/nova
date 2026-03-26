"""Pipeline integration tests."""

from __future__ import annotations

import pytest

from nova.types import EvaluationRequest
from tests.conftest import update_workspace


@pytest.mark.asyncio
async def test_full_pipeline_allow(kernel, workspace, agent) -> None:
    await update_workspace(
        workspace.id,
        rules={"can_do": ["send_email"], "cannot_do": []},
        thresholds={"auto_allow": 30, "escalate": 60, "auto_block": 90},
    )
    result = await kernel.evaluate(
        EvaluationRequest(agent_id=agent.id, workspace_id=workspace.id, action="send_email", payload={"to": "ops@example.com", "body": "hello"})
    )
    assert result.decision.action.value == "ALLOW"


@pytest.mark.asyncio
async def test_full_pipeline_block(kernel, workspace, agent) -> None:
    await update_workspace(
        workspace.id,
        rules={"can_do": [], "cannot_do": ["send_email"]},
        thresholds={"auto_allow": 30, "escalate": 60, "auto_block": 90},
    )
    result = await kernel.evaluate(
        EvaluationRequest(agent_id=agent.id, workspace_id=workspace.id, action="send_email", payload={"to": "ops@example.com", "body": "hello"})
    )
    assert result.decision.action.value == "BLOCK"


@pytest.mark.asyncio
async def test_full_pipeline_escalate(kernel, workspace, agent) -> None:
    await update_workspace(
        workspace.id,
        rules={"can_do": [], "cannot_do": []},
        thresholds={"auto_allow": 10, "escalate": 25, "auto_block": 90},
    )
    result = await kernel.evaluate(
        EvaluationRequest(
            agent_id=agent.id,
            workspace_id=workspace.id,
            action="access_user_data",
            payload={"email": "alice@example.com", "password": "secret=verybad"},
        )
    )
    assert result.decision.action.value == "ESCALATE"


@pytest.mark.asyncio
async def test_quota_exceeded(kernel, workspace, agent) -> None:
    await update_workspace(workspace.id, usage_this_month=workspace.quota_monthly)
    result = await kernel.evaluate(
        EvaluationRequest(agent_id=agent.id, workspace_id=workspace.id, action="send_email", payload={"to": "ops@example.com"})
    )
    assert result.metadata["code"] == "QUOTA_EXCEEDED"
