"""Validation and parsing helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def safe_json_loads(raw: str | None, default: Any = None) -> Any:
    """Load JSON with a safe default on parse failure."""

    if raw is None or raw == "":
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def ensure_subpath(root: Path, candidate: Path) -> Path:
    """Ensure a candidate path stays within a configured root."""

    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    if resolved_root not in resolved_candidate.parents and resolved_candidate != resolved_root:
        raise ValueError(f"path {candidate} is outside {root}")
    return resolved_candidate
