"""Per-evaluation working memory."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class WorkingMemory:
    """Stores short-lived evaluation context."""

    def __init__(self) -> None:
        self._store: defaultdict[str, dict[str, Any]] = defaultdict(dict)

    async def put(self, eval_id: str, key: str, value: Any) -> None:
        self._store[eval_id][key] = value

    async def get(self, eval_id: str, key: str) -> Any:
        return self._store.get(eval_id, {}).get(key)

    async def clear(self, eval_id: str) -> None:
        self._store.pop(eval_id, None)
