"""Cache layer with in-memory fallback."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CacheItem:
    value: Any
    expires_at: float | None = None


class MemoryCache:
    """Small in-memory cache used when Redis is not configured."""

    def __init__(self) -> None:
        self._store: dict[str, CacheItem] = {}

    def get(self, key: str) -> Any:
        item = self._store.get(key)
        if item is None:
            return None
        if item.expires_at is not None and item.expires_at < time.time():
            self._store.pop(key, None)
            return None
        return item.value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        self._store[key] = CacheItem(value=value, expires_at=expires_at)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
