from __future__ import annotations

import errno
from pathlib import Path

import pytest


def _test_config(tmp_path: Path):
    from nova.config import NovaConfig

    return NovaConfig(
        NOVA_WORKSPACE_ROOT=tmp_path,
        NOVA_DATA_DIR=tmp_path / "data",
        NOVA_DB_URL=f"sqlite+aiosqlite:///{tmp_path / 'nova.db'}",
    )


@pytest.mark.asyncio
async def test_kernel_start_attaches_to_existing_runtime_before_binding(monkeypatch, capsys, tmp_path: Path) -> None:
    from nova.kernel import NovaKernel

    kernel = NovaKernel(_test_config(tmp_path))

    async def fake_initialize() -> None:
        kernel._initialized = True

    async def fake_probe() -> dict[str, object]:
        return {
            "status": "operational",
            "version": "4.0.2",
            "active_agents": 2,
            "uptime_seconds": 42,
        }

    monkeypatch.setattr(kernel, "initialize", fake_initialize)
    monkeypatch.setattr(kernel, "_probe_existing_runtime_status", fake_probe)
    monkeypatch.setattr("nova.utils.browser.open_url", lambda url: False)

    await kernel.start(open_browser=False)

    output = capsys.readouterr().out
    assert "NOVA OS ONLINE" in output
    assert "Existing runtime already active" in output
    assert "Agents:      2" in output


@pytest.mark.asyncio
async def test_kernel_start_converts_bridge_port_conflict_to_attach(monkeypatch, capsys, tmp_path: Path) -> None:
    import nova.bridge.bridge_server as bridge_server
    from nova.kernel import NovaKernel

    kernel = NovaKernel(_test_config(tmp_path))
    probe_calls = {"count": 0}

    async def fake_initialize() -> None:
        kernel._initialized = True

    async def fake_probe() -> dict[str, object] | None:
        probe_calls["count"] += 1
        if probe_calls["count"] == 1:
            return None
        return {
            "status": "operational",
            "version": "4.0.2",
            "active_agents": 1,
            "uptime_seconds": 7,
        }

    async def fake_bridge_start(self) -> None:
        raise OSError(errno.EADDRINUSE, "address already in use")

    monkeypatch.setattr(kernel, "initialize", fake_initialize)
    monkeypatch.setattr(kernel, "_probe_existing_runtime_status", fake_probe)
    monkeypatch.setattr(bridge_server.NovaBridge, "start", fake_bridge_start)
    monkeypatch.setattr("nova.utils.browser.open_url", lambda url: False)

    await kernel.start(open_browser=False)

    output = capsys.readouterr().out
    assert "NOVA OS ONLINE" in output
    assert "Existing runtime already active" in output
    assert probe_calls["count"] == 2
