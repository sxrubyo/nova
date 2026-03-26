"""Hash-chain integrity tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nova.ledger.action_record import LedgerEntry
from nova.ledger.hash_chain import HashChain
from nova.storage.database import session_scope
from nova.storage.models import AgentModel, WorkspaceModel
from nova.utils.crypto import generate_api_key
from nova.workspace.permissions import hash_password


async def _seed_workspace_and_agent() -> tuple[str, str]:
    async with session_scope() as session:
        workspace = WorkspaceModel(
            id="ws_chain",
            name="Chain",
            slug="chain",
            plan="free",
            quota_monthly=100,
            usage_this_month=0,
            rules={"can_do": [], "cannot_do": []},
            thresholds={"auto_allow": 30, "escalate": 60, "auto_block": 80},
            risk_profile={"business_hours_start": 8, "business_hours_end": 18, "timezone": "UTC"},
            api_key=generate_api_key(),
            owner_email="chain@example.com",
            owner_name="Chain Admin",
            password_hash=hash_password("secret"),
            role="admin",
        )
        agent = AgentModel(
            id="agent_chain",
            workspace_id=workspace.id,
            name="agent-chain",
            model="gpt-4o-mini",
            provider="openai",
            status="active",
            description="",
            capabilities=[],
            permissions=[],
            extra_metadata={},
        )
        session.add(workspace)
        session.add(agent)
    return "ws_chain", "agent_chain"


@pytest.mark.asyncio
async def test_genesis_block(kernel) -> None:
    workspace_id, agent_id = await _seed_workspace_and_agent()
    chain = HashChain()
    record = await chain.record(
        LedgerEntry(
            eval_id="eval_genesis",
            agent_id=agent_id,
            workspace_id=workspace_id,
            action_type="send_email",
            payload={"body": "hello"},
            risk_score=12,
            decision="ALLOW",
            sensitivity_flags=[],
            anomalies=[],
            timestamp=datetime.now(timezone.utc),
        )
    )
    assert record.previous_hash is None


@pytest.mark.asyncio
async def test_chain_links(kernel) -> None:
    workspace_id, agent_id = await _seed_workspace_and_agent()
    chain = HashChain()
    first = await chain.record(LedgerEntry("eval_1", agent_id, workspace_id, "send_email", {"body": "hello"}, 10, "ALLOW", [], [], datetime.now(timezone.utc)))
    second = await chain.record(LedgerEntry("eval_2", agent_id, workspace_id, "send_email", {"body": "hello 2"}, 15, "ALLOW", [], [], datetime.now(timezone.utc)))
    assert second.previous_hash == first.hash


@pytest.mark.asyncio
async def test_verify_valid_chain(kernel) -> None:
    workspace_id, agent_id = await _seed_workspace_and_agent()
    chain = HashChain()
    await chain.record(LedgerEntry("eval_3", agent_id, workspace_id, "send_email", {"body": "hello"}, 10, "ALLOW", [], [], datetime.now(timezone.utc)))
    await chain.record(LedgerEntry("eval_4", agent_id, workspace_id, "send_email", {"body": "hello 2"}, 15, "ALLOW", [], [], datetime.now(timezone.utc)))
    verification = await chain.verify_integrity(workspace_id)
    assert verification.is_valid is True


@pytest.mark.asyncio
async def test_tamper_detection(kernel) -> None:
    workspace_id, agent_id = await _seed_workspace_and_agent()
    chain = HashChain()
    record = await chain.record(LedgerEntry("eval_5", agent_id, workspace_id, "send_email", {"body": "hello"}, 10, "ALLOW", [], [], datetime.now(timezone.utc)))
    async with session_scope() as session:
        ledger_model = await session.get(__import__("nova.storage.models", fromlist=["LedgerRecordModel"]).LedgerRecordModel, record.action_id)
        assert ledger_model is not None
        ledger_model.hash = "tampered"
    verification = await chain.verify_integrity(workspace_id)
    assert verification.is_valid is False
