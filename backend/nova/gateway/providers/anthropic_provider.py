"""Anthropic provider."""

from __future__ import annotations

import time
from typing import Any

import httpx

from nova.constants import DEFAULT_PROVIDER_MODELS
from nova.gateway.provider_base import BaseProvider
from nova.types import LLMResponse, ProviderState
from nova.utils.retry import retry_async


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: str) -> None:
        super().__init__(
            name="anthropic",
            api_key=api_key,
            models=DEFAULT_PROVIDER_MODELS["anthropic"],
            base_url="https://api.anthropic.com/v1/messages",
            cost_per_1k_tokens=0.015,
            health_url="https://api.anthropic.com",
        )

    def _auth_headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}

    async def complete(self, messages: list[dict[str, Any]], model: str | None, **kwargs: Any) -> LLMResponse:
        if not self.configured:
            raise RuntimeError("anthropic is not configured")
        resolved_model = model or self.models[0]

        async def _request() -> LLMResponse:
            started = time.monotonic()
            system_messages = [item["content"] for item in messages if item["role"] == "system"]
            non_system = [item for item in messages if item["role"] != "system"]
            async with httpx.AsyncClient(timeout=kwargs.get("timeout", 30.0)) as client:
                response = await client.post(
                    self.base_url,
                    headers={**self._auth_headers(), "Content-Type": "application/json"},
                    json={
                        "model": resolved_model,
                        "max_tokens": kwargs.get("max_tokens", 1000),
                        "messages": non_system,
                        "system": system_messages[0] if system_messages else None,
                    },
                )
                response.raise_for_status()
                payload = response.json()
            latency_ms = (time.monotonic() - started) * 1000
            self.latency_ms = latency_ms
            self.status = ProviderState.ONLINE
            return LLMResponse(
                provider=self.name,
                model=resolved_model,
                content=payload["content"][0]["text"],
                latency_ms=latency_ms,
                raw=payload,
                usage=payload.get("usage", {}),
            )

        return await retry_async(_request, attempts=3, base_delay=0.4)
