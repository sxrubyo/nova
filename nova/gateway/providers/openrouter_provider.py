"""OpenRouter provider."""

from __future__ import annotations

from nova.constants import DEFAULT_PROVIDER_MODELS
from nova.gateway.provider_base import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str) -> None:
        super().__init__(
            name="openrouter",
            api_key=api_key,
            models=DEFAULT_PROVIDER_MODELS["openrouter"],
            base_url="https://openrouter.ai/api/v1/chat/completions",
            cost_per_1k_tokens=0.004,
            health_url="https://openrouter.ai",
        )
