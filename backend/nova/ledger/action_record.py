"""Ledger record models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class LedgerEntry:
    """Input data required to append to the ledger."""

    eval_id: str
    agent_id: str
    workspace_id: str
    action_type: str
    payload: dict[str, Any]
    risk_score: int
    decision: str
    sensitivity_flags: list[str]
    anomalies: list[str]
    timestamp: datetime
