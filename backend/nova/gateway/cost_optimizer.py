"""Cost-aware provider selection."""

from __future__ import annotations

from nova.types import ProviderState


class CostOptimizer:
    """Select the cheapest provider that is currently usable."""

    def choose(self, providers: list[object]) -> list[object]:
        available = [provider for provider in providers if provider.status != ProviderState.UNCONFIGURED]
        return sorted(available, key=lambda provider: provider.cost_per_1k_tokens)
