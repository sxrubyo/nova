"""Agent schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str
    model: str
    provider: str
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    name: str | None = None
    model: str | None = None
    provider: str | None = None
    description: str | None = None
    status: str | None = None
    capabilities: list[str] | None = None
    permissions: list[str] | None = None
    metadata: dict[str, Any] | None = None


class ManagedAgentPermissions(BaseModel):
    can_do: list[str] = Field(default_factory=list)
    cannot_do: list[str] = Field(default_factory=list)


class ManagedAgentThresholds(BaseModel):
    auto_allow: int = 30
    escalate: int = 60
    auto_block: int = 80


class ManagedAgentQuota(BaseModel):
    max_evaluations_per_day: int = 0
    max_tokens_per_request: int = 0


class ManagedAgentCreate(BaseModel):
    name: str
    type: str
    model: str
    workspace_id: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    permissions: ManagedAgentPermissions = Field(default_factory=ManagedAgentPermissions)
    risk_thresholds: ManagedAgentThresholds = Field(default_factory=ManagedAgentThresholds)
    quota: ManagedAgentQuota = Field(default_factory=ManagedAgentQuota)
