"""Risk engine tests."""

from __future__ import annotations

import pytest

from nova.core.risk_engine import RiskEngine
from nova.types import BurstCheckResult, LoopCheckResult, RuleValidationResult, SensitivityResult, WorkspaceRiskProfile


@pytest.mark.asyncio
async def test_low_risk_action() -> None:
    engine = RiskEngine()
    score = await engine.calculate(
        intent=type("Intent", (), {"action_type": "send_email"})(),
        rule_result=RuleValidationResult(violated=False, rule_name="send_email", matched_can_do=True),
        sensitivity=SensitivityResult(),
        loop_detected=LoopCheckResult(is_loop=False, similarity=0.0, repeated_actions=0),
        burst_detected=BurstCheckResult(is_burst=False, requests_in_window=1, window_seconds=60),
        agent_history=[{"action": "send_email", "risk_score": 12}],
        workspace_risk_profile=WorkspaceRiskProfile(),
        agent_evaluation_count=150,
    )
    assert score.value < 30


@pytest.mark.asyncio
async def test_high_risk_with_pii() -> None:
    engine = RiskEngine()
    score = await engine.calculate(
        intent=type("Intent", (), {"action_type": "access_user_data"})(),
        rule_result=RuleValidationResult(violated=False, rule_name=None, matched_can_do=False),
        sensitivity=SensitivityResult(flags=["pii", "credential"], severity="critical"),
        loop_detected=LoopCheckResult(is_loop=False, similarity=0.0, repeated_actions=0),
        burst_detected=BurstCheckResult(is_burst=False, requests_in_window=1, window_seconds=60),
        agent_history=[],
        workspace_risk_profile=WorkspaceRiskProfile(),
        agent_evaluation_count=1,
    )
    assert score.value > 60


@pytest.mark.asyncio
async def test_critical_rule_violation() -> None:
    engine = RiskEngine()
    score = await engine.calculate(
        intent=type("Intent", (), {"action_type": "delete_database"})(),
        rule_result=RuleValidationResult(violated=True, rule_name="delete_database", severity="critical", detail="forbidden", matched_can_do=False),
        sensitivity=SensitivityResult(),
        loop_detected=LoopCheckResult(is_loop=False, similarity=0.0, repeated_actions=0),
        burst_detected=BurstCheckResult(is_burst=False, requests_in_window=1, window_seconds=60),
        agent_history=[],
        workspace_risk_profile=WorkspaceRiskProfile(),
        agent_evaluation_count=1,
    )
    assert score.value > 80


@pytest.mark.asyncio
async def test_score_bounds() -> None:
    engine = RiskEngine()
    score = await engine.calculate(
        intent=type("Intent", (), {"action_type": "anything"})(),
        rule_result=RuleValidationResult(violated=True, rule_name="block", severity="critical", detail="critical", matched_can_do=False),
        sensitivity=SensitivityResult(flags=["api_key", "pii", "credential", "financial"], severity="critical"),
        loop_detected=LoopCheckResult(is_loop=True, similarity=0.9, repeated_actions=8),
        burst_detected=BurstCheckResult(is_burst=True, requests_in_window=100, window_seconds=60),
        agent_history=[{"action": "anything", "risk_score": 95}] * 10,
        workspace_risk_profile=WorkspaceRiskProfile(),
        agent_evaluation_count=1,
    )
    assert 0 <= score.value <= 100


@pytest.mark.asyncio
async def test_factor_breakdown() -> None:
    engine = RiskEngine()
    score = await engine.calculate(
        intent=type("Intent", (), {"action_type": "access_user_data"})(),
        rule_result=RuleValidationResult(violated=False, rule_name=None, matched_can_do=False),
        sensitivity=SensitivityResult(flags=["pii"], severity="medium"),
        loop_detected=LoopCheckResult(is_loop=False, similarity=0.0, repeated_actions=0),
        burst_detected=BurstCheckResult(is_burst=False, requests_in_window=1, window_seconds=60),
        agent_history=[],
        workspace_risk_profile=WorkspaceRiskProfile(),
        agent_evaluation_count=1,
    )
    assert set(score.breakdown) == {"rule_layer", "sensitivity_layer", "behavior_layer"}
    assert score.breakdown["rule_layer"] >= 0
