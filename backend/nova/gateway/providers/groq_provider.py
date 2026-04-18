"""Groq provider."""

from __future__ import annotations

from nova.constants import DEFAULT_PROVIDER_MODELS
from nova.gateway.provider_base import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str) -> None:
        super().__init__(
            name="groq",
            api_key=api_key,
            models=DEFAULT_PROVIDER_MODELS["groq"],
            base_url="https://api.groq.com/openai/v1/chat/completions",
            cost_per_1k_tokens=0.0015,
            health_url="https://api.groq.com",
        )
