"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from nova.api.server import create_app
from nova.config import NovaConfig
from nova.kernel import NovaKernel
from nova.storage.database import session_scope
from nova.storage.models import WorkspaceModel


@pytest.fixture
def test_config(tmp_path: Path) -> NovaConfig:
    return NovaConfig(
        NOVA_DB_URL=f"sqlite+aiosqlite:///{tmp_path / 'nova-test.db'}",
        NOVA_WORKSPACE_ROOT=tmp_path,
        NOVA_DATA_DIR=tmp_path / "data",
        NOVA_LOG_FORMAT="console",
        NOVA_DISCOVERY_ENABLED=False,
    )


@pytest_asyncio.fixture
async def kernel(test_config: NovaConfig) -> NovaKernel:
    instance = NovaKernel(test_config)
    await instance.initialize()
    workspace = await instance.workspace_manager.ensure_default_workspace()
    agents = await instance.agent_registry.list(workspace.id)
    if not agents:
        await instance.agent_registry.create(
            workspace_id=workspace.id,
            name="test-agent",
            model="gpt-4o-mini",
            provider="openai",
            capabilities=["send_email", "generate_response"],
        )
    yield instance
    await instance.shutdown()


@pytest_asyncio.fixture
async def workspace(kernel: NovaKernel):
    return await kernel.workspace_manager.ensure_default_workspace()


@pytest_asyncio.fixture
async def agent(kernel: NovaKernel, workspace):
    agents = await kernel.agent_registry.list(workspace.id)
    return agents[0]


@pytest_asyncio.fixture
async def api_client(kernel: NovaKernel):
    app = create_app(kernel)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


async def update_workspace(workspace_id: str, **updates: object) -> None:
    async with session_scope() as session:
        workspace = await session.get(WorkspaceModel, workspace_id)
        assert workspace is not None
        for key, value in updates.items():
            setattr(workspace, key, value)
