"""Persistent core memory."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class CoreMemory:
    """Stores long-lived system and workspace facts."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = defaultdict(dict)

    async def put(self, scope: str, key: str, value: dict[str, Any]) -> None:
        self._store[scope][key] = value

    async def get(self, scope: str, key: str) -> dict[str, Any] | None:
        return self._store.get(scope, {}).get(key)
