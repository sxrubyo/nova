"""xAI provider."""

from __future__ import annotations

from nova.constants import DEFAULT_PROVIDER_MODELS
from nova.gateway.provider_base import OpenAICompatibleProvider


class XAIProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str) -> None:
        super().__init__(
            name="xai",
            api_key=api_key,
            models=DEFAULT_PROVIDER_MODELS["xai"],
            base_url="https://api.x.ai/v1/chat/completions",
            cost_per_1k_tokens=0.006,
            health_url="https://api.x.ai",
        )
