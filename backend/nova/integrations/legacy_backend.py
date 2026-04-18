"""Bridge the legacy backend API to the modular Nova runtime."""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from nova.config import NovaConfig
from nova.kernel import NovaKernel, get_kernel
from nova.storage.database import session_scope
from nova.storage.models import WorkspaceModel
from nova.storage.repositories.workspace_repo import WorkspaceRepository
from nova.types import AgentRecord, EvaluationRequest, EvaluationResult, ProviderState, WorkspacePlan, WorkspaceRecord
from nova.utils.crypto import generate_api_key
from nova.workspace.permissions import hash_password

DEFAULT_RUNTIME_WORKSPACE_RULES = {
    "can_do": [
        "generate_response",
        "execute_nova_command",
        "query_database",
        "call_external_api",
        "send_email",
        "modify_file",
    ],
    "cannot_do": [
        "exfiltrate_secrets",
        "delete_production_data",
        "drop_database",
    ],
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _runtime_db_url() -> str:
    env_value = os.getenv("NOVA_RUNTIME_DB_URL") or os.getenv("NOVA_DB_URL")
    if env_value:
        return env_value
    database_url = os.getenv("DATABASE_URL", "")
    if database_url:
        if database_url.startswith("postgresql://"):
            return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if database_url.startswith("postgres://"):
            return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        if database_url.startswith("sqlite:///"):
            return database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        return database_url
    return f"sqlite+aiosqlite:///{_repo_root() / 'nova.db'}"


def runtime_config() -> NovaConfig:
    """Build the config used when the legacy backend embeds the runtime."""

    repo_root = _repo_root()
    return NovaConfig(
        db_url=_runtime_db_url(),
        workspace_root=repo_root,
        data_dir=repo_root / "data",
    )


async def get_runtime_kernel() -> NovaKernel:
    """Return an initialized kernel configured for the shared project runtime."""

    kernel = get_kernel(runtime_config())
    await kernel.initialize()
    return kernel


def _slugify(value: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return base or "workspace"


def _normalize_plan(value: Any) -> WorkspacePlan:
    try:
        return WorkspacePlan(str(value).lower())
    except ValueError:
        return WorkspacePlan.ENTERPRISE


async def ensure_workspace_synced(legacy_workspace: dict[str, Any]) -> WorkspaceRecord:
    """Mirror a legacy backend workspace into the modular runtime database."""

    kernel = await get_runtime_kernel()
    workspace_id = str(legacy_workspace["id"])
    existing = await kernel.workspace_manager.get_workspace(workspace_id)
    if existing is not None:
        return existing

    async with session_scope() as session:
        repo = WorkspaceRepository(session)
        current = await repo.get(workspace_id)
        if current is None:
            current = WorkspaceModel(
                id=workspace_id,
                name=str(legacy_workspace.get("name") or "Legacy Workspace"),
                slug=f"{_slugify(str(legacy_workspace.get('name') or 'legacy'))}-{workspace_id[:8]}",
                plan=_normalize_plan(legacy_workspace.get("plan")).value,
                quota_monthly=100_000,
                usage_this_month=0,
                rules=DEFAULT_RUNTIME_WORKSPACE_RULES,
                thresholds={
                    "auto_allow": kernel.config.auto_allow_threshold,
                    "escalate": kernel.config.escalate_threshold,
                    "auto_block": kernel.config.auto_block_threshold,
                },
                risk_profile={
                    "business_hours_start": 8,
                    "business_hours_end": 18,
                    "timezone": "UTC",
                },
                api_key=legacy_workspace.get("api_key") or generate_api_key(kernel.config.api_key_prefix),
                owner_email=str(legacy_workspace.get("email") or f"{workspace_id}@legacy.nova"),
                owner_name=str(legacy_workspace.get("name") or "Legacy Workspace"),
                password_hash=hash_password(workspace_id),
                role="admin",
            )
            await repo.create(current)
        else:
            current.name = str(legacy_workspace.get("name") or current.name)
            current.plan = _normalize_plan(legacy_workspace.get("plan")).value
            current.api_key = legacy_workspace.get("api_key") or current.api_key
            current.owner_email = str(legacy_workspace.get("email") or current.owner_email)
            current.owner_name = str(legacy_workspace.get("name") or current.owner_name)
            current.rules = current.rules or DEFAULT_RUNTIME_WORKSPACE_RULES
            await session.flush()
    synced = await kernel.workspace_manager.get_workspace(workspace_id)
    if synced is None:
        raise RuntimeError(f"failed to synchronize runtime workspace {workspace_id}")
    return synced


async def ensure_agent_synced(
    legacy_workspace: dict[str, Any],
    agent_name: str,
    *,
    description: str = "",
    model: str = "openai/gpt-4o-mini",
    provider: str = "openrouter",
    can_do: list[str] | None = None,
    cannot_do: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentRecord:
    """Mirror a legacy agent definition into the runtime registry."""

    kernel = await get_runtime_kernel()
    workspace = await ensure_workspace_synced(legacy_workspace)
    agent = await kernel.agent_registry.ensure(
        workspace_id=workspace.id,
        name=agent_name,
        model=model,
        provider=provider,
        description=description,
        capabilities=["legacy-backend", "dashboard"],
        permissions=can_do or ["generate_response"],
        metadata={**dict(metadata or {}), "cannot_do": list(cannot_do or [])},
    )
    return agent


@contextmanager
def temporary_provider_key(kernel: NovaKernel, provider_name: str | None, api_key: str | None):
    """Temporarily override a provider API key for one request."""

    if not provider_name or not api_key:
        yield
        return
    provider = kernel.gateway.providers.get(provider_name)
    if provider is None:
        yield
        return
    previous_key = provider.api_key
    previous_status = provider.status
    provider.api_key = api_key
    provider.status = ProviderState.DEGRADED
    try:
        yield
    finally:
        provider.api_key = previous_key
        provider.status = previous_status


async def evaluate_action(
    legacy_workspace: dict[str, Any],
    *,
    agent_name: str,
    action: str,
    payload: dict[str, Any],
    description: str = "",
    model: str = "openai/gpt-4o-mini",
    provider: str = "openrouter",
    api_key: str | None = None,
    can_do: list[str] | None = None,
    cannot_do: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    request_id: str | None = None,
    source: str = "legacy-backend",
) -> tuple[AgentRecord, EvaluationResult]:
    """Evaluate a legacy backend action through the modular runtime."""

    kernel = await get_runtime_kernel()
    workspace = await ensure_workspace_synced(legacy_workspace)
    agent = await ensure_agent_synced(
        legacy_workspace,
        agent_name,
        description=description,
        model=model,
        provider=provider,
        can_do=can_do,
        cannot_do=cannot_do,
        metadata=metadata,
    )
    with temporary_provider_key(kernel, provider, api_key):
        result = await kernel.evaluate(
            EvaluationRequest(
                agent_id=agent.id,
                workspace_id=workspace.id,
                action=action,
                payload=payload,
                source=source,
                request_id=request_id,
            )
        )
    return agent, result
