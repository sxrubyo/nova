"""Cohere provider."""

from __future__ import annotations

import time
from typing import Any

import httpx

from nova.constants import DEFAULT_PROVIDER_MODELS
from nova.gateway.provider_base import BaseProvider
from nova.types import LLMResponse, ProviderState
from nova.utils.retry import retry_async


class CohereProvider(BaseProvider):
    def __init__(self, api_key: str) -> None:
        super().__init__(
            name="cohere",
            api_key=api_key,
            models=DEFAULT_PROVIDER_MODELS["cohere"],
            base_url="https://api.cohere.ai/v2/chat",
            cost_per_1k_tokens=0.008,
            health_url="https://api.cohere.ai",
        )

    async def complete(self, messages: list[dict[str, Any]], model: str | None, **kwargs: Any) -> LLMResponse:
        if not self.configured:
            raise RuntimeError("cohere is not configured")
        resolved_model = model or self.models[0]

        async def _request() -> LLMResponse:
            started = time.monotonic()
            prompt = "\n".join(f"{item['role']}: {item['content']}" for item in messages)
            async with httpx.AsyncClient(timeout=kwargs.get("timeout", 30.0)) as client:
                response = await client.post(
                    self.base_url,
                    headers={**self._auth_headers(), "Content-Type": "application/json"},
                    json={"model": resolved_model, "message": prompt},
                )
                response.raise_for_status()
                payload = response.json()
            latency_ms = (time.monotonic() - started) * 1000
            self.latency_ms = latency_ms
            self.status = ProviderState.ONLINE
            content = payload.get("message", {}).get("content", [{}])[0].get("text", "")
            return LLMResponse(
                provider=self.name,
                model=resolved_model,
                content=content,
                latency_ms=latency_ms,
                raw=payload,
                usage=payload.get("usage", {}),
            )

        return await retry_async(_request, attempts=3, base_delay=0.4)
