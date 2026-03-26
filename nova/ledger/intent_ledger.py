"""Ledger orchestration for Nova evaluations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nova.ledger.action_record import LedgerEntry
from nova.ledger.hash_chain import HashChain
from nova.storage.database import session_scope
from nova.storage.repositories.ledger_repo import LedgerRepository
from nova.types import LedgerRecord


class IntentLedger:
    """High-level append-only ledger API."""

    def __init__(self) -> None:
        self.hash_chain = HashChain()

    async def record(
        self,
        eval_id: str,
        agent_id: str,
        workspace_id: str,
        intent: Any,
        risk_score: Any,
        decision: Any,
        sensitivity_flags: list[str],
        anomalies: list[str],
        timestamp: datetime,
        payload: dict[str, Any] | None = None,
    ) -> LedgerRecord:
        return await self.hash_chain.record(
            LedgerEntry(
                eval_id=eval_id,
                agent_id=agent_id,
                workspace_id=workspace_id,
                action_type=intent.action_type,
                payload=payload or intent.parameters,
                risk_score=risk_score.value,
                decision=decision.action.value,
                sensitivity_flags=sensitivity_flags,
                anomalies=anomalies,
                timestamp=timestamp,
            )
        )

    async def record_completion(self, eval_id: str, result: Any) -> None:
        async with session_scope() as session:
            repo = LedgerRepository(session)
            model = await repo.get_by_eval_id(eval_id)
            if model:
                model.result = result.output if hasattr(result, "output") else result
                model.completed_at = datetime.now(timezone.utc)

    async def record_error(self, eval_id: str, error: str) -> None:
        async with session_scope() as session:
            repo = LedgerRepository(session)
            model = await repo.get_by_eval_id(eval_id)
            if model:
                model.error = error
                model.completed_at = datetime.now(timezone.utc)

    async def list_entries(self, workspace_id: str, limit: int = 100) -> list[Any]:
        async with session_scope() as session:
            repo = LedgerRepository(session)
            return await repo.list_by_workspace(workspace_id, limit)

    async def get_entry(self, action_id: str) -> Any:
        async with session_scope() as session:
            repo = LedgerRepository(session)
            return await repo.get(action_id)
