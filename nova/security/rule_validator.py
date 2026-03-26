"""Rule validation against workspace policy."""

from __future__ import annotations

from nova.types import AgentRecord, IntentAnalysis, RuleValidationResult, WorkspaceRules


class RuleValidator:
    """Validate intents against allow and deny lists."""

    async def validate(
        self,
        intent: IntentAnalysis,
        agent: AgentRecord,
        workspace_rules: WorkspaceRules,
    ) -> RuleValidationResult:
        target = f"{intent.action_type} {intent.raw_action} {intent.target}".lower()
        agent_cannot_do = [str(rule) for rule in agent.metadata.get("cannot_do", [])]
        cannot_do_rules = [*agent_cannot_do, *workspace_rules.cannot_do]
        can_do_rules = [*agent.permissions, *workspace_rules.can_do]
        for rule in cannot_do_rules:
            if rule.lower() in target:
                return RuleValidationResult(
                    violated=True,
                    rule_name=rule,
                    severity="critical",
                    detail=f"matched cannot_do rule `{rule}`",
                    matched_can_do=False,
                )
        for rule in can_do_rules:
            if rule.lower() in target:
                return RuleValidationResult(
                    violated=False,
                    rule_name=rule,
                    severity="none",
                    detail=f"matched can_do rule `{rule}`",
                    matched_can_do=True,
                )
        return RuleValidationResult(
            violated=False,
            rule_name=None,
            severity="none",
            detail="no explicit rule matched",
            matched_can_do=False,
        )
