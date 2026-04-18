"""Text and payload utilities."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any


def flatten_payload(payload: Any) -> str:
    """Convert nested payloads to a search-friendly string."""

    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        return " ".join(f"{key} {flatten_payload(value)}" for key, value in payload.items())
    if isinstance(payload, Iterable) and not isinstance(payload, (bytes, bytearray)):
        return " ".join(flatten_payload(item) for item in payload)
    return str(payload)


def tokenize(value: str) -> set[str]:
    """Tokenize text into a lowercase word set."""

    return {token for token in re.findall(r"[a-zA-Z0-9_/-]+", value.lower()) if token}


def jaccard_similarity(a: str, b: str) -> float:
    """Compute Jaccard similarity between two strings."""

    set_a = tokenize(a)
    set_b = tokenize(b)
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def detect_action_type(action: str, payload: dict[str, Any]) -> str:
    """Infer a normalized action type from action text and payload."""

    lowered = action.lower().strip()
    if lowered.startswith("nova ") or "command" in lowered or "cli" in lowered:
        return "execute_nova_command"
    if any(word in lowered for word in {"email", "correo"}):
        return "send_email"
    if any(word in lowered for word in {"database", "sql", "query"}):
        return "query_database"
    if any(word in lowered for word in {"api", "http", "webhook"}):
        return "call_external_api"
    if any(word in lowered for word in {"file", "archivo", "write", "modify"}):
        return "modify_file"
    if "messages" in payload or "prompt" in payload or "response" in lowered:
        return "generate_response"
    return lowered.replace(" ", "_") or "generic_action"


def extract_target(action: str, payload: dict[str, Any]) -> str:
    """Infer a target resource from action text or payload."""

    if "url" in payload:
        return str(payload["url"])
    if "path" in payload:
        return str(payload["path"])
    if "table" in payload:
        return str(payload["table"])
    if "model" in payload:
        return str(payload["model"])
    return action.split(" ", 1)[-1] if " " in action else action


def truncate(value: str, max_length: int = 280) -> str:
    """Truncate text to a fixed width for logs and summaries."""

    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3]}..."
