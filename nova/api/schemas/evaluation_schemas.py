"""Evaluation schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvaluateRequestSchema(BaseModel):
    agent_id: str
    action: str
    payload: dict = Field(default_factory=dict)
    workspace_id: str | None = None
