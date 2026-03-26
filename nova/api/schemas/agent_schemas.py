"""Agent schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str
    model: str
    provider: str
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)


class AgentUpdate(BaseModel):
    name: str | None = None
    model: str | None = None
    provider: str | None = None
    description: str | None = None
    status: str | None = None
    capabilities: list[str] | None = None
