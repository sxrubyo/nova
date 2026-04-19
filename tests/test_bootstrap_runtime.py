"""Tests for the portable Nova bootstrap runtime."""

from __future__ import annotations

from pathlib import Path


def test_bootstrap_runtime_paths_live_under_nova_home(tmp_path: Path) -> None:
    from nova.bootstrap import runtime_root, runtime_python_path

    root = runtime_root(tmp_path)

    assert root == tmp_path / ".nova" / "runtime"
    assert runtime_python_path(root).is_relative_to(root)


def test_wrapper_script_uses_runtime_python_and_repo_path(tmp_path: Path) -> None:
    from nova.bootstrap import build_wrapper_script

    repo_dir = tmp_path / "nova-os"
    runtime_python = tmp_path / ".nova" / "runtime" / "bin" / "python"

    script = build_wrapper_script(runtime_python, repo_dir)

    assert str(runtime_python) in script
    assert str(repo_dir / "nova.py") in script
    assert '"$@"' in script


def test_ensure_runtime_prefers_venv_over_system_pip(tmp_path: Path) -> None:
    from nova.bootstrap import ensure_runtime

    calls: list[list[str]] = []
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "requirements.txt").write_text("fastapi\n", encoding="utf-8")

    def fake_run(command: list[str], **_: object) -> None:
        calls.append(command)

    ensure_runtime(
        repo_dir=repo_dir,
        home_dir=tmp_path,
        python_bin="/usr/bin/python3",
        command_runner=fake_run,
    )

    assert calls[0][:3] == ["/usr/bin/python3", "-m", "venv"]
    assert calls[1][0].endswith("/.nova/runtime/bin/python")
    assert calls[1][1:4] == ["-m", "pip", "install"]
    assert "--upgrade" in calls[1]
    assert calls[2][0].endswith("/.nova/runtime/bin/python")
    assert calls[2][1:4] == ["-m", "pip", "install"]
    assert "-r" in calls[2]
