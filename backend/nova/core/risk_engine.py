"""Configurable multi-layer risk scoring engine."""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean

from nova.types import BurstCheckResult, LoopCheckResult, RiskFactor, RiskLevel, RiskScore, RuleValidationResult, SensitivityResult, WorkspaceRiskProfile


class RiskEngine:
    """Compute a 0-100 risk score from rules, sensitivity, and behavior."""

    def __init__(self, rule_weight: float = 0.40, sensitivity_weight: float = 0.35, behavior_weight: float = 0.25) -> None:
        self.rule_weight = rule_weight
        self.sensitivity_weight = sensitivity_weight
        self.behavior_weight = behavior_weight

    async def calculate(
        self,
        intent: object,
        rule_result: RuleValidationResult,
        sensitivity: SensitivityResult,
        loop_detected: LoopCheckResult,
        burst_detected: BurstCheckResult,
        agent_history: list[dict[str, object]],
        workspace_risk_profile: WorkspaceRiskProfile,
        agent_evaluation_count: int = 0,
    ) -> RiskScore:
        rule_layer = 0
        sensitivity_layer = 0
        behavior_layer = 0
        factors: list[RiskFactor] = []
        recommendations: list[str] = []

        if rule_result.matched_can_do:
            rule_layer = 0
            factors.append(RiskFactor("can_do_match", -20, rule_result.detail))
        elif rule_result.violated:
            rule_layer = 100 if rule_result.severity == "critical" else 80
            factors.append(RiskFactor("cannot_do_match", 80, rule_result.detail))
            recommendations.append("Restrict or pause the agent until the rule violation is reviewed.")
        else:
            rule_layer = 35
            factors.append(RiskFactor("no_explicit_rule_match", 15, "action is not explicitly allowed"))

        if sensitivity.flags:
            multiplier = 1.15 if len(set(sensitivity.flags)) > 1 else 1.0
            if "api_key" in sensitivity.flags:
                sensitivity_layer += int(70 * multiplier)
                factors.append(RiskFactor("api_key_detected", 70 * multiplier, "payload contains API-key like material"))
            if "pii" in sensitivity.flags:
                sensitivity_layer += int(60 * multiplier)
                factors.append(RiskFactor("pii_detected", 60 * multiplier, "payload contains personally identifiable information"))
            if "financial" in sensitivity.flags:
                sensitivity_layer += int(85 * multiplier)
                factors.append(RiskFactor("financial_data_detected", 85 * multiplier, "payload contains financial data"))
            if "credential" in sensitivity.flags:
                sensitivity_layer += int(90 * multiplier)
                factors.append(RiskFactor("credential_detected", 90 * multiplier, "payload contains credentials"))
            sensitivity_layer = min(sensitivity_layer, 100)
            recommendations.append("Redact or tokenize sensitive data before execution.")

        if loop_detected.is_loop:
            behavior_layer += 70
            factors.append(RiskFactor("loop_detected", 20, f"similarity {loop_detected.similarity:.2f}"))
        if burst_detected.is_burst:
            behavior_layer += 75
            factors.append(RiskFactor("burst_detected", 25, f"{burst_detected.requests_in_window} req/{burst_detected.window_seconds}s"))

        history_scores = [int(item.get("risk_score", 0)) for item in agent_history if "risk_score" in item]
        if history_scores and mean(history_scores[:10]) > 60:
            behavior_layer += 40
            factors.append(RiskFactor("historically_risky", 15, "recent average risk score is above 60"))

        if agent_evaluation_count < 100:
            behavior_layer += 10
            factors.append(RiskFactor("new_agent", 5, "agent has fewer than 100 evaluations"))

        current_hour = datetime.now(timezone.utc).hour
        if current_hour < workspace_risk_profile.business_hours_start or current_hour >= workspace_risk_profile.business_hours_end:
            behavior_layer += 20
            factors.append(RiskFactor("time_anomaly", 10, "action occurred outside workspace business hours"))

        historical_actions = {str(item.get("action", "")) for item in agent_history}
        if getattr(intent, "action_type", "") not in historical_actions:
            behavior_layer += 15
            factors.append(RiskFactor("first_time_action", 5, "agent has not executed this action recently"))
        behavior_layer = min(behavior_layer, 100)

        raw_score = (
            rule_layer * self.rule_weight
            + sensitivity_layer * self.sensitivity_weight
            + behavior_layer * self.behavior_weight
            + workspace_risk_profile.sensitivity_bias
        )
        final_score = max(0, min(100, int(round(raw_score))))
        if rule_result.violated and rule_result.severity == "critical":
            final_score = max(final_score, 90)
        elif "pii" in sensitivity.flags and len(sensitivity.flags) >= 2:
            final_score = max(final_score, 65)
        if final_score >= 80:
            level = RiskLevel.CRITICAL
        elif final_score >= 60:
            level = RiskLevel.HIGH
        elif final_score >= 30:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        if not recommendations and final_score >= 60:
            recommendations.append("Route this evaluation to a human reviewer.")

        return RiskScore(
            value=final_score,
            level=level,
            factors=factors,
            breakdown={
                "rule_layer": max(rule_layer, 0),
                "sensitivity_layer": max(sensitivity_layer, 0),
                "behavior_layer": max(behavior_layer, 0),
            },
            recommendations=recommendations,
        )
