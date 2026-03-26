"""Gateway router tests."""

from __future__ import annotations

import pytest

from nova.config import NovaConfig
from nova.gateway.router import GatewayRouter
from nova.observability.alerts import AlertManager
from nova.types import LLMRequest, LLMResponse, ProviderState


class FakeProvider:
    def __init__(self, name: str, *, fail: bool = False) -> None:
        self.name = name
        self.fail = fail
        self.status = ProviderState.ONLINE
        self.configured = True
        self.latency_ms = 10.0
        self.cost_per_1k_tokens = 0.01
        self.models = ["fake-model"]
        self.last_error = None

    async def complete(self, messages, model, **kwargs):
        if self.fail:
            raise RuntimeError(f"{self.name} failed")
        return LLMResponse(provider=self.name, model=model or "fake-model", content="ok", latency_ms=5.0)

    async def health_check(self):
        self.status = ProviderState.ONLINE
        return True

    def snapshot(self):
        return {"name": self.name, "status": self.status.value}


@pytest.mark.asyncio
async def test_failover() -> None:
    router = GatewayRouter(NovaConfig(), AlertManager())
    router.providers = {"first": FakeProvider("first", fail=True), "second": FakeProvider("second")}
    response = await router.route(LLMRequest(messages=[{"role": "user", "content": "hi"}]))
    assert response.provider == "second"


@pytest.mark.asyncio
async def test_all_providers_fail() -> None:
    router = GatewayRouter(NovaConfig(), AlertManager())
    router.providers = {"first": FakeProvider("first", fail=True), "second": FakeProvider("second", fail=True)}
    with pytest.raises(Exception):
        await router.route(LLMRequest(messages=[{"role": "user", "content": "hi"}]))


@pytest.mark.asyncio
async def test_health_check() -> None:
    router = GatewayRouter(NovaConfig(), AlertManager())
    router.providers = {"first": FakeProvider("first")}
    router.health_checker.providers = list(router.providers.values())
    await router.health_checker.check_once()
    assert router.providers["first"].status == ProviderState.ONLINE
