"""Intent analyzer tests."""

from __future__ import annotations

import pytest

from nova.core.intent_analyzer import IntentAnalyzer
from nova.types import AgentRecord, AgentStatus


@pytest.mark.asyncio
async def test_parse_simple_action() -> None:
    analyzer = IntentAnalyzer()
    agent = AgentRecord(id="a1", workspace_id="w1", name="alpha", model="gpt-4o-mini", provider="openai", status=AgentStatus.ACTIVE)
    result = await analyzer.analyze("send email", {"to": "user@example.com"}, agent)
    assert result.action_type == "send_email"


@pytest.mark.asyncio
async def test_parse_complex_payload() -> None:
    analyzer = IntentAnalyzer()
    agent = AgentRecord(id="a1", workspace_id="w1", name="alpha", model="gpt-4o-mini", provider="openai", status=AgentStatus.ACTIVE)
    result = await analyzer.analyze("generate response", {"messages": [{"role": "user", "content": "hi"}], "model": "openai/gpt-4o-mini"}, agent)
    assert result.target_provider == "openai"
    assert "messages" in result.parameters
