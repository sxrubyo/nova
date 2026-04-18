"""Bridge protocol models."""

from __future__ import annotations

from pydantic import BaseModel


class BridgeMessage(BaseModel):
    type: str
    agent_id: str | None = None
    action: str | None = None
    payload: dict = {}
    capabilities: list[str] = []
