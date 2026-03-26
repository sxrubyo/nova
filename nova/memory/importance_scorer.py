"""Importance scoring for memory entries."""

from __future__ import annotations

from nova.types import Decision, DecisionAction, RiskScore


class ImportanceScorer:
    """Assign a 1-10 importance score to evaluation events."""

    def score(self, risk_score: RiskScore, decision: Decision) -> int:
        if decision.action == DecisionAction.BLOCK:
            return 9 if risk_score.value >= 80 else 7
        if decision.action == DecisionAction.ESCALATE:
            return 6
        if risk_score.value < 30:
            return 2
        if risk_score.value < 60:
            return 4
        return 5
