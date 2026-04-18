"""Gmail-oriented helper routes backed by the Nova ledger."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from nova.api.dependencies import get_current_workspace, get_kernel_dependency
from nova.kernel import NovaKernel

router = APIRouter()


@router.get("/api/gmail/check-duplicate")
async def check_duplicate_email(
    recipient: str = Query(..., min_length=3),
    subject: str = Query(..., min_length=1),
    timeframe_hours: int = Query(24, ge=1, le=24 * 30),
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    """Check whether an allowed send_email action already targeted the same recipient and subject."""

    recipient_key = recipient.strip().casefold()
    subject_key = subject.strip().casefold()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=timeframe_hours)
    entries = await kernel.ledger.list_entries(current_workspace["workspace_id"], limit=500)

    for entry in entries:
        if entry.action_type != "send_email":
            continue
        if str(entry.decision).upper() != "ALLOW":
            continue
        entry_timestamp = entry.timestamp
        if entry_timestamp.tzinfo is None:
            entry_timestamp = entry_timestamp.replace(tzinfo=timezone.utc)
        if entry_timestamp < cutoff:
            continue

        record_metadata = dict(entry.record_metadata or {})
        dedupe_keys = dict(record_metadata.get("dedupe_keys") or {})
        if dedupe_keys.get("recipient") != recipient_key:
            continue
        if dedupe_keys.get("subject") != subject_key:
            continue

        return {
            "is_duplicate": True,
            "recipient": recipient,
            "subject": subject,
            "last_sent_at": entry_timestamp.isoformat(),
            "action_id": entry.action_id,
            "eval_id": entry.eval_id,
            "ledger_hash": entry.hash,
        }

    return {
        "is_duplicate": False,
        "recipient": recipient,
        "subject": subject,
        "timeframe_hours": timeframe_hours,
    }
