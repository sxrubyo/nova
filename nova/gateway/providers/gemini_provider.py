"""Gemini provider."""

from __future__ import annotations

from nova.constants import DEFAULT_PROVIDER_MODELS
from nova.gateway.provider_base import OpenAICompatibleProvider


class GeminiProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str) -> None:
        super().__init__(
            name="gemini",
            api_key=api_key,
            models=DEFAULT_PROVIDER_MODELS["gemini"],
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            cost_per_1k_tokens=0.003,
            health_url="https://generativelanguage.googleapis.com",
        )
