"""Discovery route schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DiscoveryConnectRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class DiscoveryTaskRequest(BaseModel):
    prompt: str
    model: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    approval_mode: str = "suggest"
    working_directory: str | None = None
    timeout: int | None = 300
