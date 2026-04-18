"""Latency-aware provider ordering."""

from __future__ import annotations


class LoadBalancer:
    """Prioritize providers with the lowest observed latency."""

    def order(self, providers: list[object]) -> list[object]:
        return sorted(providers, key=lambda provider: provider.latency_ms or 1_000_000)
