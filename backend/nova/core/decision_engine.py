"""Decision engine for allow/block/escalate outcomes."""

from __future__ import annotations

from nova.types import Decision, DecisionAction, EvaluationContext, RiskScore, WorkspaceThresholds


class DecisionEngine:
    """Map risk scores to decisions using workspace thresholds."""

    async def decide(self, risk_score: RiskScore, context: EvaluationContext, thresholds: WorkspaceThresholds) -> Decision:
        if risk_score.value >= thresholds.auto_block:
            return Decision(
                action=DecisionAction.BLOCK,
                reason=f"risk score {risk_score.value} exceeds auto-block threshold {thresholds.auto_block}",
                requires_human=False,
            )
        if risk_score.value >= thresholds.escalate:
            return Decision(
                action=DecisionAction.ESCALATE,
                reason=f"risk score {risk_score.value} exceeds escalation threshold {thresholds.escalate}",
                requires_human=True,
            )
        return Decision(
            action=DecisionAction.ALLOW,
            reason=f"risk score {risk_score.value} is within auto-allow range",
            requires_human=False,
        )
