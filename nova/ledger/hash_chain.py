"""Cryptographic hash-chain implementation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from nova.ledger.action_record import LedgerEntry
from nova.storage.database import session_scope
from nova.storage.models import LedgerRecordModel
from nova.storage.repositories.ledger_repo import LedgerRepository
from nova.nova_types import LedgerRecord
from nova.utils.crypto import generate_id, sha256_hex, sign_entry, stable_json
from nova.utils.text import flatten_payload, truncate


def _email_dedupe_keys(action_type: str, payload: dict[str, object]) -> dict[str, str]:
    if action_type != "send_email":
        return {}

    recipient = ""
    for key in ("recipient", "to", "email", "recipientEmail"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            recipient = value.strip().casefold()
            break

    subject = ""
    for key in ("subject", "emailSubject"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            subject = value.strip().casefold()
            break

    dedupe: dict[str, str] = {}
    if recipient:
        dedupe["recipient"] = recipient
    if subject:
        dedupe["subject"] = subject
    return dedupe


@dataclass(slots=True)
class ChainVerification:
    """Verification result for a ledger hash chain."""

    is_valid: bool
    total_records: int
    verified_records: int
    broken_at: str | None
    verified_at: datetime


class HashChain:
    """Immutable ledger chain based on SHA-256 hashes."""

    @staticmethod
    def _record_signature(
        *,
        eval_id: str,
        agent_id: str,
        action_type: str,
        payload_digest: str,
        timestamp_iso: str,
        risk_score: int,
        decision: str,
        previous_hash: str | None,
    ) -> str:
        return sign_entry(
            {
                "eval_id": eval_id,
                "agent_id": agent_id,
                "action_type": action_type,
                "payload_digest": payload_digest,
                "timestamp_iso": timestamp_iso,
                "risk_score": risk_score,
                "decision": decision,
                "previous_hash": previous_hash or "NOVA_GENESIS_BLOCK",
            },
            os.environ.get("NOVA_LEDGER_SECRET"),
        )

    async def record(self, entry: LedgerEntry) -> LedgerRecord:
        async with session_scope() as session:
            repo = LedgerRepository(session)
            previous = await repo.latest(entry.workspace_id)
            previous_hash = previous.hash if previous else None
            payload_digest = sha256_hex(stable_json(entry.payload))
            dedupe_keys = _email_dedupe_keys(entry.action_type, entry.payload)
            current_hash = self._record_signature(
                eval_id=entry.eval_id,
                agent_id=entry.agent_id,
                action_type=entry.action_type,
                payload_digest=payload_digest,
                timestamp_iso=entry.timestamp.isoformat(),
                risk_score=entry.risk_score,
                decision=entry.decision,
                previous_hash=previous_hash,
            )
            action_id = generate_id("act")
            model = LedgerRecordModel(
                action_id=action_id,
                eval_id=entry.eval_id,
                agent_id=entry.agent_id,
                workspace_id=entry.workspace_id,
                action_type=entry.action_type,
                payload_summary=truncate(flatten_payload(entry.payload), 280),
                risk_score=entry.risk_score,
                decision=entry.decision,
                sensitivity_flags=entry.sensitivity_flags,
                anomalies=entry.anomalies,
                hash=current_hash,
                previous_hash=previous_hash,
                record_metadata={
                    "payload_digest": payload_digest,
                    "timestamp_iso": entry.timestamp.isoformat(),
                    "dedupe_keys": dedupe_keys,
                },
                timestamp=entry.timestamp,
            )
            await repo.add(model)
            return LedgerRecord(
                action_id=action_id,
                eval_id=entry.eval_id,
                agent_id=entry.agent_id,
                workspace_id=entry.workspace_id,
                action_type=entry.action_type,
                risk_score=entry.risk_score,
                decision=entry.decision,
                sensitivity_flags=list(entry.sensitivity_flags),
                anomalies=list(entry.anomalies),
                hash=current_hash,
                previous_hash=previous_hash,
                timestamp=entry.timestamp,
                payload_summary=model.payload_summary,
            )

    async def verify_integrity(self, workspace_id: str) -> ChainVerification:
        async with session_scope() as session:
            repo = LedgerRepository(session)
            records = await repo.ordered_chain(workspace_id)
            broken_at = None
            verified_count = 0
            for index, record in enumerate(records):
                expected_prev = records[index - 1].hash if index > 0 else None
                if record.previous_hash != expected_prev:
                    broken_at = record.action_id
                    break
                record_metadata = record.record_metadata or {}
                payload_digest = str(record_metadata.get("payload_digest", ""))
                timestamp_iso = str(record_metadata.get("timestamp_iso", record.timestamp.isoformat()))
                recomputed = self._record_signature(
                    eval_id=record.eval_id,
                    agent_id=record.agent_id,
                    action_type=record.action_type,
                    payload_digest=payload_digest,
                    timestamp_iso=timestamp_iso,
                    risk_score=record.risk_score,
                    decision=record.decision,
                    previous_hash=expected_prev,
                )
                if recomputed != record.hash:
                    broken_at = record.action_id
                    break
                verified_count += 1
            return ChainVerification(
                is_valid=broken_at is None,
                total_records=len(records),
                verified_records=verified_count,
                broken_at=broken_at,
                verified_at=datetime.now(timezone.utc),
            )
