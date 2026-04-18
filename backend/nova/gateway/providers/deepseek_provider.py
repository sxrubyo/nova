"""DeepSeek provider."""

from __future__ import annotations

from nova.constants import DEFAULT_PROVIDER_MODELS
from nova.gateway.provider_base import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str) -> None:
        super().__init__(
            name="deepseek",
            api_key=api_key,
            models=DEFAULT_PROVIDER_MODELS["deepseek"],
            base_url="https://api.deepseek.com/v1/chat/completions",
            cost_per_1k_tokens=0.0025,
            health_url="https://api.deepseek.com",
        )
