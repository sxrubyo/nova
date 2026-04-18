"""Gateway router with failover across providers."""

from __future__ import annotations

import asyncio
from typing import Any

from nova.config import NovaConfig
from nova.gateway.cost_optimizer import CostOptimizer
from nova.gateway.health_checker import ProviderHealthChecker
from nova.gateway.load_balancer import LoadBalancer
from nova.gateway.providers.anthropic_provider import AnthropicProvider
from nova.gateway.providers.cohere_provider import CohereProvider
from nova.gateway.providers.deepseek_provider import DeepSeekProvider
from nova.gateway.providers.gemini_provider import GeminiProvider
from nova.gateway.providers.groq_provider import GroqProvider
from nova.gateway.providers.mistral_provider import MistralProvider
from nova.gateway.providers.openai_provider import OpenAIProvider
from nova.gateway.providers.openrouter_provider import OpenRouterProvider
from nova.gateway.providers.xai_provider import XAIProvider
from nova.observability.alerts import AlertManager
from nova.observability.logger import get_logger
from nova.types import IntentAnalysis, LLMRequest, LLMResponse, ProviderState


class GatewayRouter:
    """Multi-provider router with cost and latency-based failover."""

    def __init__(self, config: NovaConfig, alerts: AlertManager) -> None:
        self.config = config
        self.logger = get_logger("nova.gateway")
        self.providers = {
            "openai": OpenAIProvider(config.openai_api_key),
            "anthropic": AnthropicProvider(config.anthropic_api_key),
            "gemini": GeminiProvider(config.google_api_key),
            "groq": GroqProvider(config.groq_api_key),
            "openrouter": OpenRouterProvider(config.openrouter_api_key),
            "xai": XAIProvider(config.xai_api_key),
            "mistral": MistralProvider(config.mistral_api_key),
            "deepseek": DeepSeekProvider(config.deepseek_api_key),
            "cohere": CohereProvider(config.cohere_api_key),
        }
        self.cost_optimizer = CostOptimizer()
        self.load_balancer = LoadBalancer()
        self.health_checker = ProviderHealthChecker(list(self.providers.values()), alerts, config.health_check_interval_seconds)

    async def start(self) -> None:
        await self.health_checker.start()

    async def stop(self) -> None:
        await self.health_checker.stop()

    def get_optimal_provider(self, intent: IntentAnalysis) -> str | None:
        if intent.target_provider and intent.target_provider in self.providers:
            return intent.target_provider
        if intent.action_type == "generate_response":
            ordered = self.cost_optimizer.choose(list(self.providers.values()))
        else:
            ordered = self.load_balancer.order(list(self.providers.values()))
        for provider in ordered:
            if provider.status != ProviderState.UNCONFIGURED:
                return provider.name
        return None

    async def route(self, request: LLMRequest) -> LLMResponse:
        chain = self._get_failover_chain(request)
        last_error: Exception | None = None
        for provider in chain:
            if provider.status == ProviderState.OFFLINE:
                continue
            try:
                return await asyncio.wait_for(
                    provider.complete(request.messages, request.model, timeout=request.timeout or self.config.http_timeout_seconds),
                    timeout=request.timeout or self.config.http_timeout_seconds,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                provider.status = ProviderState.DEGRADED if provider.configured else ProviderState.UNCONFIGURED
                provider.last_error = str(exc)
                self.logger.warning("provider_failed", provider=provider.name, error=str(exc))
        from nova.exceptions import AllProvidersFailedError

        raise AllProvidersFailedError(code="ALL_PROVIDERS_FAILED", message=str(last_error or "no provider available"))

    def _get_failover_chain(self, request: LLMRequest) -> list[object]:
        if request.provider and request.provider in self.providers:
            primary = self.providers[request.provider]
            others = [provider for name, provider in self.providers.items() if name != request.provider]
            return [primary, *self.load_balancer.order(others)]
        ordered = self.cost_optimizer.choose(list(self.providers.values()))
        return self.load_balancer.order(ordered)

    def status(self) -> list[dict[str, Any]]:
        return [
            {
                "name": provider.name,
                "status": provider.status.value,
                "latency_ms": round(provider.latency_ms, 2),
                "cost_per_1k_tokens": provider.cost_per_1k_tokens,
                "models": provider.models,
                "last_error": provider.last_error,
            }
            for provider in self.providers.values()
        ]
