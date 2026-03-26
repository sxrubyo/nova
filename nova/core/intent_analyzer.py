"""Intent parsing and normalization."""

from __future__ import annotations

from typing import Any

from nova.types import AgentRecord, IntentAnalysis
from nova.utils.text import detect_action_type, extract_target


class IntentAnalyzer:
    """Heuristically parse incoming agent actions."""

    async def analyze(self, action: str, payload: dict[str, Any], agent_context: AgentRecord) -> IntentAnalysis:
        action_type = detect_action_type(action, payload)
        target_provider = payload.get("provider")
        if target_provider is None and payload.get("model"):
            model = str(payload["model"])
            if "/" in model:
                target_provider = model.split("/", 1)[0]
            else:
                target_provider = agent_context.provider
        return IntentAnalysis(
            action_type=action_type,
            target=extract_target(action, payload),
            target_provider=target_provider,
            parameters=payload,
            inferred_purpose=f"{agent_context.name} wants to perform `{action_type}`",
            confidence=0.82,
            raw_action=action,
        )
