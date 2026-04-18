"""Mistral provider."""

from __future__ import annotations

from nova.constants import DEFAULT_PROVIDER_MODELS
from nova.gateway.provider_base import OpenAICompatibleProvider


class MistralProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str) -> None:
        super().__init__(
            name="mistral",
            api_key=api_key,
            models=DEFAULT_PROVIDER_MODELS["mistral"],
            base_url="https://api.mistral.ai/v1/chat/completions",
            cost_per_1k_tokens=0.007,
            health_url="https://api.mistral.ai",
        )
