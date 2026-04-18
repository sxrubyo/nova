"""Workspace lifecycle management."""

from __future__ import annotations

import re

from nova.config import NovaConfig
from nova.storage.database import session_scope
from nova.storage.models import WorkspaceModel
from nova.storage.repositories.workspace_repo import WorkspaceRepository
from nova.types import WorkspacePlan, WorkspaceRecord, WorkspaceRiskProfile, WorkspaceRules, WorkspaceThresholds
from nova.utils.crypto import generate_api_key, generate_id
from nova.workspace.permissions import hash_password


class WorkspaceManager:
    """Creates and retrieves workspace entities."""

    def __init__(self, config: NovaConfig) -> None:
        self.config = config

    async def list_workspaces(self) -> list[WorkspaceRecord]:
        async with session_scope() as session:
            repo = WorkspaceRepository(session)
            return [self._to_record(item) for item in await repo.list_all()]

    async def get_workspace(self, workspace_id: str) -> WorkspaceRecord | None:
        async with session_scope() as session:
            repo = WorkspaceRepository(session)
            item = await repo.get(workspace_id)
            return self._to_record(item) if item else None

    async def get_by_email(self, email: str) -> WorkspaceModel | None:
        async with session_scope() as session:
            repo = WorkspaceRepository(session)
            return await repo.get_by_email(email)

    async def get_by_api_key(self, api_key: str) -> WorkspaceModel | None:
        async with session_scope() as session:
            repo = WorkspaceRepository(session)
            return await repo.get_by_api_key(api_key)

    async def create_workspace(
        self,
        name: str,
        owner_email: str,
        owner_name: str,
        password: str,
        plan: WorkspacePlan = WorkspacePlan.FREE,
    ) -> WorkspaceRecord:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or generate_id("ws")
        async with session_scope() as session:
            repo = WorkspaceRepository(session)
            workspace = WorkspaceModel(
                id=generate_id("ws"),
                name=name,
                slug=slug,
                plan=plan.value,
                quota_monthly={
                    WorkspacePlan.FREE: 1_000,
                    WorkspacePlan.PRO: 10_000,
                    WorkspacePlan.ENTERPRISE: 100_000,
                }[plan],
                usage_this_month=0,
                rules={"can_do": [], "cannot_do": []},
                thresholds={
                    "auto_allow": self.config.auto_allow_threshold,
                    "escalate": self.config.escalate_threshold,
                    "auto_block": self.config.auto_block_threshold,
                },
                risk_profile={"business_hours_start": 8, "business_hours_end": 18, "timezone": "UTC"},
                api_key=generate_api_key(self.config.api_key_prefix),
                owner_email=owner_email,
                owner_name=owner_name,
                password_hash=hash_password(password),
                role="admin",
            )
            await repo.create(workspace)
            return self._to_record(workspace)

    async def ensure_default_workspace(self) -> WorkspaceRecord:
        async with session_scope() as session:
            repo = WorkspaceRepository(session)
            existing = await repo.get_by_slug("default")
            if existing:
                return self._to_record(existing)
            workspace = WorkspaceModel(
                id=generate_id("ws"),
                name="Default Workspace",
                slug="default",
                plan=WorkspacePlan.ENTERPRISE.value,
                quota_monthly=100_000,
                usage_this_month=0,
                rules={"can_do": ["generate_response", "query_database"], "cannot_do": ["exfiltrate_secrets"]},
                thresholds={
                    "auto_allow": self.config.auto_allow_threshold,
                    "escalate": self.config.escalate_threshold,
                    "auto_block": self.config.auto_block_threshold,
                },
                risk_profile={"business_hours_start": 8, "business_hours_end": 18, "timezone": "UTC"},
                api_key=generate_api_key(self.config.api_key_prefix),
                owner_email="admin@nova.local",
                owner_name="Nova Admin",
                password_hash=hash_password("nova-admin"),
                role="admin",
            )
            await repo.create(workspace)
            return self._to_record(workspace)

    def _to_record(self, model: WorkspaceModel) -> WorkspaceRecord:
        return WorkspaceRecord(
            id=model.id,
            name=model.name,
            slug=model.slug,
            plan=WorkspacePlan(model.plan),
            quota_monthly=model.quota_monthly,
            usage_this_month=model.usage_this_month,
            rules=WorkspaceRules(**(model.rules or {})),
            thresholds=WorkspaceThresholds(**(model.thresholds or {})),
            risk_profile=WorkspaceRiskProfile(**(model.risk_profile or {})),
            api_key=model.api_key,
            created_at=model.created_at,
        )
