"""Agent registration and lookup."""

from __future__ import annotations

from nova.storage.database import session_scope
from nova.storage.models import AgentModel
from nova.storage.repositories.agent_repo import AgentRepository
from nova.storage.repositories.workspace_repo import WorkspaceRepository
from nova.types import AgentRecord, AgentStatus, WorkspaceRecord, WorkspaceRiskProfile, WorkspaceRules, WorkspaceThresholds, WorkspacePlan
from nova.utils.crypto import generate_id


class AgentRegistry:
    """Tracks registered agents."""

    async def list(self, workspace_id: str) -> list[AgentRecord]:
        async with session_scope() as session:
            repo = AgentRepository(session)
            return [self._to_record(agent) for agent in await repo.list_by_workspace(workspace_id)]

    async def get(self, agent_id: str) -> AgentRecord | None:
        async with session_scope() as session:
            repo = AgentRepository(session)
            agent = await repo.get(agent_id)
            return self._to_record(agent) if agent else None

    async def create(
        self,
        workspace_id: str,
        name: str,
        model: str,
        provider: str,
        description: str = "",
        capabilities: list[str] | None = None,
    ) -> AgentRecord:
        async with session_scope() as session:
            workspace_repo = WorkspaceRepository(session)
            workspace = await workspace_repo.get(workspace_id)
            if workspace is None:
                raise ValueError(f"workspace {workspace_id} not found")
            repo = AgentRepository(session)
            agent = AgentModel(
                id=generate_id("agent"),
                workspace_id=workspace_id,
                name=name,
                model=model,
                provider=provider,
                status=AgentStatus.ACTIVE.value,
                description=description,
                capabilities=capabilities or [],
                permissions=[],
                extra_metadata={},
            )
            await repo.create(agent)
            agent.workspace = workspace
            return self._to_record(agent)

    async def ensure(
        self,
        workspace_id: str,
        name: str,
        model: str,
        provider: str,
        description: str = "",
        capabilities: list[str] | None = None,
        permissions: list[str] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> AgentRecord:
        async with session_scope() as session:
            workspace_repo = WorkspaceRepository(session)
            workspace = await workspace_repo.get(workspace_id)
            if workspace is None:
                raise ValueError(f"workspace {workspace_id} not found")
            repo = AgentRepository(session)
            existing = await repo.get_by_workspace_and_name(workspace_id, name)
            if existing is not None:
                existing.model = model
                existing.provider = provider
                existing.description = description
                existing.capabilities = capabilities or list(existing.capabilities or [])
                existing.permissions = permissions or list(existing.permissions or [])
                existing.extra_metadata = {**dict(existing.extra_metadata or {}), **dict(metadata or {})}
                existing.status = AgentStatus.ACTIVE.value
                existing.workspace = workspace
                await session.flush()
                return self._to_record(existing)
            agent = AgentModel(
                id=generate_id("agent"),
                workspace_id=workspace_id,
                name=name,
                model=model,
                provider=provider,
                status=AgentStatus.ACTIVE.value,
                description=description,
                capabilities=capabilities or [],
                permissions=permissions or [],
                extra_metadata=metadata or {},
            )
            await repo.create(agent)
            agent.workspace = workspace
            return self._to_record(agent)

    async def update(self, agent_id: str, **changes: object) -> AgentRecord | None:
        async with session_scope() as session:
            repo = AgentRepository(session)
            agent = await repo.get(agent_id)
            if agent is None:
                return None
            for key, value in changes.items():
                if value is not None and hasattr(agent, key):
                    setattr(agent, key, value)
            await session.flush()
            return self._to_record(agent)

    async def delete(self, agent_id: str) -> bool:
        async with session_scope() as session:
            repo = AgentRepository(session)
            return await repo.delete(agent_id)

    async def pause(self, agent_id: str) -> AgentRecord | None:
        return await self.update(agent_id, status=AgentStatus.PAUSED.value)

    async def resume(self, agent_id: str) -> AgentRecord | None:
        return await self.update(agent_id, status=AgentStatus.ACTIVE.value)

    def _to_record(self, model: AgentModel | None) -> AgentRecord | None:
        if model is None:
            return None
        workspace_record = None
        if model.workspace is not None:
            workspace_record = WorkspaceRecord(
                id=model.workspace.id,
                name=model.workspace.name,
                slug=model.workspace.slug,
                plan=WorkspacePlan(model.workspace.plan),
                quota_monthly=model.workspace.quota_monthly,
                usage_this_month=model.workspace.usage_this_month,
                rules=WorkspaceRules(**(model.workspace.rules or {})),
                thresholds=WorkspaceThresholds(**(model.workspace.thresholds or {})),
                risk_profile=WorkspaceRiskProfile(**(model.workspace.risk_profile or {})),
                api_key=model.workspace.api_key,
                created_at=model.workspace.created_at,
            )
        return AgentRecord(
            id=model.id,
            workspace_id=model.workspace_id,
            name=model.name,
            model=model.model,
            provider=model.provider,
            status=AgentStatus(model.status),
            description=model.description,
            capabilities=list(model.capabilities or []),
            permissions=list(model.permissions or []),
            metadata=dict(model.extra_metadata or {}),
            evaluation_count=model.evaluation_count,
            last_seen_at=model.last_seen_at,
            created_at=model.created_at,
            workspace=workspace_record,
        )
