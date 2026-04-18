"""Execute approved actions through the appropriate provider or adapter."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from nova.config import NovaConfig
from nova.gateway.router import GatewayRouter
from nova.types import ExecutionResult, IntentAnalysis, LLMRequest
from nova.utils.validators import ensure_subpath


class ActionExecutor:
    """Execute actions that passed the policy pipeline."""

    def __init__(self, config: NovaConfig, gateway: GatewayRouter) -> None:
        self.config = config
        self.gateway = gateway

    async def execute(self, intent: IntentAnalysis, provider: str | None, payload: dict[str, Any]) -> ExecutionResult:
        started = time.monotonic()
        if intent.action_type == "generate_response":
            messages = payload.get("messages")
            if not messages:
                prompt = str(payload.get("prompt") or payload.get("input") or "")
                messages = [{"role": "user", "content": prompt}]
            response = await self.gateway.route(
                LLMRequest(
                    messages=messages,
                    model=payload.get("model"),
                    provider=provider,
                    timeout=payload.get("timeout"),
                )
            )
            return ExecutionResult(
                provider=response.provider,
                status="completed",
                output={"content": response.content, "model": response.model, "usage": response.usage},
                latency_ms=(time.monotonic() - started) * 1000,
            )

        if intent.action_type == "call_external_api":
            if payload.get("simulate"):
                return ExecutionResult(
                    provider="httpx",
                    status="simulated",
                    output={"url": payload.get("url"), "method": payload.get("method", "GET")},
                    latency_ms=(time.monotonic() - started) * 1000,
                )
            method = str(payload.get("method", "GET")).upper()
            url = str(payload["url"])
            try:
                async with httpx.AsyncClient(timeout=payload.get("timeout", self.config.http_timeout_seconds)) as client:
                    response = await client.request(method, url, headers=payload.get("headers"), json=payload.get("body"))
            except httpx.HTTPError as exc:
                return ExecutionResult(
                    provider="httpx",
                    status="failed",
                    output={"url": url, "method": method, "error": str(exc)},
                    latency_ms=(time.monotonic() - started) * 1000,
                )
            return ExecutionResult(
                provider="httpx",
                status="completed",
                output={"status_code": response.status_code, "body": response.text[:1000]},
                latency_ms=(time.monotonic() - started) * 1000,
            )

        if intent.action_type == "modify_file":
            path = ensure_subpath(self.config.workspace_root.resolve(), Path(str(payload["path"])))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(payload.get("content", "")), encoding="utf-8")
            return ExecutionResult(
                provider="filesystem",
                status="completed",
                output={"path": str(path), "bytes_written": path.stat().st_size},
                latency_ms=(time.monotonic() - started) * 1000,
            )

        if intent.action_type == "query_database":
            database_url = str(payload.get("database_url") or self.config.db_url)
            query = str(payload.get("query", "")).strip()
            if not query.lower().startswith("select"):
                raise ValueError("only SELECT queries are allowed through the generic executor")
            engine = create_async_engine(database_url)
            async with engine.connect() as connection:
                result = await connection.execute(text(query))
                rows = [dict(row._mapping) for row in result.fetchall()]
            await engine.dispose()
            return ExecutionResult(
                provider="database",
                status="completed",
                output={"rows": rows},
                latency_ms=(time.monotonic() - started) * 1000,
            )

        if intent.action_type == "send_email":
            return ExecutionResult(
                provider="email",
                status="queued",
                output={
                    "to": payload.get("to"),
                    "subject": payload.get("subject"),
                    "body": payload.get("body"),
                },
                latency_ms=(time.monotonic() - started) * 1000,
            )

        if intent.action_type == "execute_nova_command":
            return ExecutionResult(
                provider="cli",
                status="approved",
                output={"command": payload.get("command"), "message": "command approved by nova runtime"},
                latency_ms=(time.monotonic() - started) * 1000,
            )

        return ExecutionResult(
            provider=provider,
            status="completed",
            output={"message": "action accepted", "action_type": intent.action_type, "payload": payload},
            latency_ms=(time.monotonic() - started) * 1000,
        )
