"""Ledger verification facade."""

from __future__ import annotations

from nova.ledger.hash_chain import ChainVerification, HashChain


class LedgerVerifier:
    """Facade around hash-chain verification."""

    def __init__(self, chain: HashChain) -> None:
        self.chain = chain

    async def verify(self, workspace_id: str) -> ChainVerification:
        return await self.chain.verify_integrity(workspace_id)
