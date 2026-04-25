"""Regresiones para el puente legacy de boot/doctor."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("nova_legacy_cli_module", ROOT / "legacy" / "nova_cli_legacy.py")
assert SPEC and SPEC.loader
LEGACY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LEGACY)


class _FakeSpinner:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def __enter__(self) -> "_FakeSpinner":
        return self

    def __exit__(self, *_args) -> None:
        return None

    def finish(self) -> None:
        return None


def test_check_modern_runtime_running_reports_modern_fix_command(monkeypatch) -> None:
    monkeypatch.setattr(LEGACY, "_probe_modern_runtime_status", lambda *args, **kwargs: (False, {}, "http://127.0.0.1:9800"))

    result = LEGACY._check_modern_runtime_running()

    assert result.status == LEGACY._DoctorResult.FAIL
    assert result.fix_cmd == "nova start --no-open-browser"
    assert "9800" in result.detail


def test_auto_fix_modern_runtime_starts_nova_entrypoint(monkeypatch) -> None:
    probes = iter(
        [
            (False, {}, "http://127.0.0.1:9800"),
            (True, {"status": "operational", "version": "4.0.7"}, "http://127.0.0.1:9800"),
        ]
    )
    starts: list[str] = []

    monkeypatch.setattr(LEGACY, "_probe_modern_runtime_status", lambda *args, **kwargs: next(probes))
    monkeypatch.setattr(LEGACY, "_find_nova_runtime_entrypoint", lambda: "/tmp/nova.py")
    monkeypatch.setattr(LEGACY, "_start_modern_runtime_background", lambda path=None: starts.append(path or "") or True)
    monkeypatch.setattr(LEGACY.time, "sleep", lambda *_args, **_kwargs: None)

    results = LEGACY._auto_fix_modern_runtime(auto=True)

    assert starts == ["/tmp/nova.py"]
    assert len(results) == 1
    assert results[0].status == LEGACY._DoctorResult.FIXED
    assert results[0].name == "auto-fix:nova-runtime"


def test_boot_uses_modern_runtime_flow(monkeypatch, capsys) -> None:
    probes = iter(
        [
            (False, {}, "http://127.0.0.1:9800"),
            (True, {"status": "operational", "version": "4.0.7"}, "http://127.0.0.1:9800"),
        ]
    )

    monkeypatch.setattr(LEGACY, "print_logo", lambda compact=True: None)
    monkeypatch.setattr(LEGACY, "Spinner", _FakeSpinner)
    monkeypatch.setattr(LEGACY, "_probe_modern_runtime_status", lambda *args, **kwargs: next(probes))
    monkeypatch.setattr(LEGACY, "_find_nova_runtime_entrypoint", lambda: "/tmp/nova.py")
    monkeypatch.setattr(LEGACY, "_start_modern_runtime_background", lambda _path=None: True)
    monkeypatch.setattr(LEGACY, "_find_project_root", lambda *args, **kwargs: Path("/tmp"))
    monkeypatch.setattr(LEGACY, "discover_agents", lambda *args, **kwargs: [])
    monkeypatch.setattr(LEGACY.time, "sleep", lambda *_args, **_kwargs: None)

    LEGACY.cmd_boot(SimpleNamespace(path=""))

    output = capsys.readouterr().out
    assert "nova_core.py" not in output
    assert "Nova runtime started" in output
    assert "127.0.0.1:9800" in output

