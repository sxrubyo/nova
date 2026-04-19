"""Frontend serving compatibility tests for the unified Nova runtime."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from nova.api.server import create_app
from nova.config import NovaConfig
from nova.kernel import NovaKernel


@pytest.mark.asyncio
async def test_server_serves_frontend_bundle_when_present(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text("<html><body>Nova Dashboard</body></html>", encoding="utf-8")
    (assets / "app.js").write_text("console.log('nova')", encoding="utf-8")

    config = NovaConfig(
        NOVA_DB_URL=f"sqlite+aiosqlite:///{tmp_path / 'nova-ui.db'}",
        NOVA_WORKSPACE_ROOT=tmp_path,
        NOVA_DATA_DIR=tmp_path / "data",
        NOVA_FRONTEND_DIST=dist,
        NOVA_DISCOVERY_ENABLED=False,
    )
    kernel = NovaKernel(config)
    await kernel.initialize()
    app = create_app(kernel, serve_frontend=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        root = await client.get("/")
        asset = await client.get("/assets/app.js")
        spa = await client.get("/dashboard/discover")
        status = await client.get("/api/status")

    await kernel.shutdown()

    assert root.status_code == 200
    assert "Nova Dashboard" in root.text
    assert asset.status_code == 200
    assert "console.log('nova')" in asset.text
    assert spa.status_code == 200
    assert "Nova Dashboard" in spa.text
    assert status.status_code == 200


@pytest.mark.asyncio
async def test_server_returns_json_root_without_frontend_bundle(tmp_path: Path) -> None:
    config = NovaConfig(
        NOVA_DB_URL=f"sqlite+aiosqlite:///{tmp_path / 'nova-api.db'}",
        NOVA_WORKSPACE_ROOT=tmp_path,
        NOVA_DATA_DIR=tmp_path / "data",
        NOVA_FRONTEND_DIST=tmp_path / "missing-dist",
        NOVA_DISCOVERY_ENABLED=False,
    )
    kernel = NovaKernel(config)
    await kernel.initialize()
    app = create_app(kernel, serve_frontend=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        root = await client.get("/")

    await kernel.shutdown()

    assert root.status_code == 200
    assert root.json()["name"] == "Nova OS"
