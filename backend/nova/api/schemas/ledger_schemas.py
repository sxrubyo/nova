"""Ledger schemas."""

from __future__ import annotations

from pydantic import BaseModel


class LedgerExportResponse(BaseModel):
    total_records: int
    entries: list[dict]
