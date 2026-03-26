"""Analytics schemas."""

from __future__ import annotations

from pydantic import BaseModel


class AnalyticsSummaryResponse(BaseModel):
    evaluations: int
    avg_duration_ms: float
    avg_risk_score: float
    decisions: dict[str, int]
