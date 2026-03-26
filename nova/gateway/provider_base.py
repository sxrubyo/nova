"""Base classes for LLM providers."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from nova.types import LLMResponse, ProviderHealth, ProviderState
from nova.utils.retry import retry_async


class BaseProvider(ABC):
    """Provider contract used by the gateway router."""

    def __init__(
        self,
        name: str,
        api_key: str,
        models: list[str],
        base_url: str,
        cost_per_1k_tokens: float,
        health_url: str | None = None,
    ) -> None:
        self.name = name
        self.api_key = api_key
        self.models = models
        self.base_url = base_url
        self.health_url = health_url or base_url
        self.cost_per_1k_tokens = cost_per_1k_tokens
        self.status = ProviderState.UNCONFIGURED if not api_key else ProviderState.DEGRADED
        self.latency_ms = 0.0
        self.last_error: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @abstractmethod
    async def complete(self, messages: list[dict[str, Any]], model: str | None, **kwargs: Any) -> LLMResponse:
        """Execute a completion request."""

    async def health_check(self) -> bool:
        """Best-effort provider reachability check."""

        if not self.configured:
            self.status = ProviderState.UNCONFIGURED
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.health_url, headers=self._auth_headers())
            self.status = ProviderState.ONLINE if response.status_code < 500 else ProviderState.DEGRADED
            self.last_error = None if response.status_code < 500 else f"http_{response.status_code}"
            return response.status_code < 500
        except Exception as exc:  # noqa: BLE001
            self.status = ProviderState.DEGRADED
            self.last_error = str(exc)
            return False

    def snapshot(self) -> ProviderHealth:
        """Serialize provider state."""

        return ProviderHealth(
            name=self.name,
            status=self.status,
            latency_ms=self.latency_ms,
            cost_per_1k_tokens=self.cost_per_1k_tokens,
            models=list(self.models),
            last_error=self.last_error,
        )

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}


class OpenAICompatibleProvider(BaseProvider):
    """Shared implementation for providers with OpenAI-style chat endpoints."""

    async def complete(self, messages: list[dict[str, Any]], model: str | None, **kwargs: Any) -> LLMResponse:
        if not self.configured:
            raise RuntimeError(f"{self.name} is not configured")

        resolved_model = model or self.models[0]

        async def _request() -> LLMResponse:
            started = time.monotonic()
            async with httpx.AsyncClient(timeout=kwargs.get("timeout", 30.0)) as client:
                response = await client.post(
                    self.base_url,
                    headers={**self._auth_headers(), "Content-Type": "application/json"},
                    json={
                        "model": resolved_model,
                        "messages": messages,
                        "temperature": kwargs.get("temperature", 0.1),
                        "max_tokens": kwargs.get("max_tokens", 1000),
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
                content=payload["choices"][0]["message"]["content"],
                latency_ms=latency_ms,
                raw=payload,
                usage=payload.get("usage", {}),
            )

        try:
            return await retry_async(_request, attempts=3, base_delay=0.4)
        except Exception as exc:  # noqa: BLE001
            self.status = ProviderState.DEGRADED
            self.last_error = str(exc)
            raise
