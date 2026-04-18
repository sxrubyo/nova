"""Cryptographic helpers."""

from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any

try:
    import orjson
except ImportError:  # pragma: no cover - host compatibility fallback
    orjson = None


def stable_json(data: Any) -> str:
    """Serialize data deterministically for signing and hashing."""

    if orjson is None:
        return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return orjson.dumps(data, option=orjson.OPT_SORT_KEYS).decode("utf-8")


def sha256_hex(value: str) -> str:
    """Return a SHA-256 hex digest for a string value."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def chain_hash(previous_hash: str | None, payload: dict[str, Any]) -> str:
    """Compute a ledger chain hash."""

    return sha256_hex(f"{stable_json(payload)}::{previous_hash or 'NOVA_GENESIS_BLOCK'}")


def generate_id(prefix: str) -> str:
    """Generate a short prefixed identifier."""

    return f"{prefix}_{secrets.token_hex(8)}"


def generate_api_key(prefix: str = "nova_") -> str:
    """Generate a secure API key."""

    return f"{prefix}{secrets.token_urlsafe(24)}"


def mask_secret(value: str, visible_start: int = 4, visible_end: int = 4) -> str:
    """Mask a secret while preserving a small prefix and suffix."""

    if len(value) <= visible_start + visible_end:
        return "*" * len(value)
    return f"{value[:visible_start]}{'*' * (len(value) - visible_start - visible_end)}{value[-visible_end:]}"
