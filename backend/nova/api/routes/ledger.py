"""Ledger routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from nova.api.dependencies import get_current_workspace, get_kernel_dependency
from nova.kernel import NovaKernel

router = APIRouter()


@router.get("/api/ledger/verify")
async def verify_ledger(
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    result = await kernel.ledger.hash_chain.verify_integrity(current_workspace["workspace_id"])
    return {
        "is_valid": result.is_valid,
        "total_records": result.total_records,
        "verified_records": result.verified_records,
        "broken_at": result.broken_at,
        "verified_at": result.verified_at.isoformat(),
    }


@router.get("/api/ledger/export")
async def export_ledger(
    limit: int = Query(100, ge=1, le=5000),
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    entries = await kernel.ledger.list_entries(current_workspace["workspace_id"], limit)
    return {"total_records": len(entries), "entries": [entry.payload_summary for entry in entries]}


@router.get("/api/ledger")
async def list_ledger(
    limit: int = Query(100, ge=1, le=5000),
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> list[dict]:
    entries = await kernel.ledger.list_entries(current_workspace["workspace_id"], limit)
    return [
        {
            "action_id": entry.action_id,
            "eval_id": entry.eval_id,
            "action_type": entry.action_type,
            "risk_score": entry.risk_score,
            "decision": entry.decision,
            "hash": entry.hash,
            "previous_hash": entry.previous_hash,
            "timestamp": entry.timestamp.isoformat(),
            "payload_summary": entry.payload_summary,
        }
        for entry in entries
    ]


@router.get("/api/ledger/{action_id}")
async def get_ledger_entry(
    action_id: str,
    _: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    entry = await kernel.ledger.get_entry(action_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="ledger entry not found")
    return {
        "action_id": entry.action_id,
        "eval_id": entry.eval_id,
        "action_type": entry.action_type,
        "risk_score": entry.risk_score,
        "decision": entry.decision,
        "hash": entry.hash,
        "previous_hash": entry.previous_hash,
        "timestamp": entry.timestamp.isoformat(),
        "payload_summary": entry.payload_summary,
        "result": entry.result,
        "error": entry.error,
    }
