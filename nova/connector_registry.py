"""Workspace connector inventory derived from the local Nova skill store."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nova.integrations_catalog import INTEGRATION_SCHEMAS

NON_CREDENTIAL_KEYS = {"installed_at", "skill_version", "status"}
FIELD_ALIASES = {
    "gmail": {
        "gmail_token": {"gmail_token", "service_account_json"},
    },
}


def _skills_dir() -> Path:
    return Path.home() / ".nova" / "skills"


def _safe_json(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def _configured_fields(credentials: dict[str, Any]) -> list[str]:
    return sorted(key for key, value in credentials.items() if key not in NON_CREDENTIAL_KEYS and _has_value(value))


def _required_fields(schema: dict[str, Any]) -> list[str]:
    return [field.get("key") for field in schema.get("credentials", []) if field.get("required") and field.get("key")]


def _required_fields_present(connector_key: str, required_fields: list[str], configured_fields: list[str]) -> bool:
    configured = set(configured_fields)
    aliases = FIELD_ALIASES.get(connector_key, {})
    for field in required_fields:
        acceptable = aliases.get(field, {field})
        if configured.intersection(acceptable):
            continue
        return False
    return True


def _connector_entry(key: str, schema: dict[str, Any], credential_path: Path | None, credentials: dict[str, Any]) -> dict[str, Any]:
    configured_fields = _configured_fields(credentials)
    required_fields = _required_fields(schema)
    all_required_present = _required_fields_present(key, required_fields, configured_fields) if required_fields else bool(configured_fields)
    is_connected = credential_path is not None and all_required_present
    is_partial = credential_path is not None and not is_connected
    modified_at = None
    if credential_path is not None and credential_path.exists():
        modified_at = datetime.fromtimestamp(credential_path.stat().st_mtime, tz=timezone.utc).isoformat()

    return {
        "key": key,
        "name": schema.get("name", key),
        "category": schema.get("category", "Other"),
        "description": schema.get("description", ""),
        "capabilities": list(schema.get("capabilities", [])),
        "credentials_schema": list(schema.get("credentials", [])),
        "required_fields": required_fields,
        "configured_fields": configured_fields,
        "connected": is_connected,
        "status": "connected" if is_connected else "incomplete" if is_partial else "available",
        "connected_via": "cli_credentials" if credential_path is not None else None,
        "credential_source": str(credential_path) if credential_path is not None else None,
        "setup_url": schema.get("setup_url"),
        "last_updated_at": modified_at,
    }


def build_connector_inventory() -> dict[str, Any]:
    """Return the runtime connector registry view for the current host."""

    skills_dir = _skills_dir()
    known_files = {path.stem: path for path in skills_dir.glob("*.json")} if skills_dir.exists() else {}
    connectors = [
        _connector_entry(
            key=key,
            schema=schema,
            credential_path=known_files.get(key),
            credentials=_safe_json(known_files[key]) if key in known_files else {},
        )
        for key, schema in INTEGRATION_SCHEMAS.items()
    ]

    connected_count = len([item for item in connectors if item["connected"]])
    partial_count = len([item for item in connectors if item["status"] == "incomplete"])

    return {
        "connectors": connectors,
        "summary": {
            "catalog_count": len(connectors),
            "connected_count": connected_count,
            "incomplete_count": partial_count,
            "skills_dir": str(skills_dir),
        },
    }
