"""Verify ledger integrity from the CLI."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nova.kernel import get_kernel


async def main() -> None:
    kernel = get_kernel()
    await kernel.initialize()
    workspace = await kernel.workspace_manager.ensure_default_workspace()
    result = await kernel.ledger.hash_chain.verify_integrity(workspace.id)
    print(json.dumps({"is_valid": result.is_valid, "total_records": result.total_records, "broken_at": result.broken_at}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
