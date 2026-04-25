"""Tests for the portable Nova bootstrap runtime."""

from __future__ import annotations

from pathlib import Path
import subprocess
from unittest import mock


def test_bootstrap_runtime_paths_live_under_nova_home(tmp_path: Path) -> None:
    from nova.bootstrap import repo_root, runtime_root, runtime_python_path

    root = runtime_root(tmp_path)

    assert root == tmp_path / ".nova" / "runtime"
    assert runtime_python_path(root).is_relative_to(root)
    assert repo_root(tmp_path) == tmp_path / ".nova" / "repo"


def test_wrapper_script_uses_runtime_python_and_repo_path(tmp_path: Path) -> None:
    from nova.bootstrap import build_wrapper_script

    repo_dir = tmp_path / "nova-os"
    runtime_python = tmp_path / ".nova" / "runtime" / "bin" / "python"

    script = build_wrapper_script(runtime_python, repo_dir)

    assert str(runtime_python) in script
    assert str(repo_dir / "nova.py") in script
    assert '"$@"' in script
    assert '[ "$#" -eq 0 ]' in script
    assert 'launchpad' not in script


def test_windows_wrapper_script_uses_cmd_forwarding(tmp_path: Path) -> None:
    from nova.bootstrap import build_wrapper_script

    repo_dir = tmp_path / "nova-os"
    runtime_python = tmp_path / ".nova" / "runtime" / "Scripts" / "python.exe"

    script = build_wrapper_script(runtime_python, repo_dir, windows=True)

    assert "@echo off" in script
    assert str(runtime_python) in script
    assert str(repo_dir / "nova.py") in script
    assert "%*" in script
    assert 'if "%~1"==""' in script
    assert 'launchpad' not in script


def test_bootstrap_banner_contains_nova_branding() -> None:
    from nova.bootstrap import render_bootstrap_banner

    banner = render_bootstrap_banner()

    assert "NOVA OS" in banner
    assert "launch vector" in banner
    assert "terminals" in banner
    assert "╭" in banner


def test_bootstrap_compact_banner_is_single_line() -> None:
    from nova.bootstrap import render_bootstrap_banner

    banner = render_bootstrap_banner(compact=True)

    assert "NOVA OS" in banner
    assert "bootstrap lane engaged" in banner
    assert "\n" not in banner


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


def test_ensure_runtime_skips_reinstall_when_runtime_state_matches(tmp_path: Path) -> None:
    from nova.bootstrap import ensure_runtime, runtime_python_path, runtime_root

    calls: list[list[str]] = []
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "requirements.txt").write_text("fastapi\n", encoding="utf-8")

    def fake_run(command: list[str], **_: object) -> None:
        calls.append(command)
        if command[:3] == ["/usr/bin/python3", "-m", "venv"]:
            runtime_python = runtime_python_path(runtime_root(tmp_path))
            runtime_python.parent.mkdir(parents=True, exist_ok=True)
            runtime_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    ensure_runtime(
        repo_dir=repo_dir,
        home_dir=tmp_path,
        python_bin="/usr/bin/python3",
        command_runner=fake_run,
    )
    first_run = list(calls)

    ensure_runtime(
        repo_dir=repo_dir,
        home_dir=tmp_path,
        python_bin="/usr/bin/python3",
        command_runner=fake_run,
    )

    assert len(first_run) == 3
    assert calls == first_run


def test_ensure_runtime_prefers_core_requirements_profile_when_available(tmp_path: Path) -> None:
    from nova.bootstrap import ensure_runtime

    calls: list[list[str]] = []
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    (repo_dir / "nova_core_requirements.txt").write_text("fastapi\nrich\n", encoding="utf-8")

    def fake_run(command: list[str], **_: object) -> None:
        calls.append(command)

    ensure_runtime(
        repo_dir=repo_dir,
        home_dir=tmp_path,
        python_bin="/usr/bin/python3",
        command_runner=fake_run,
    )

    assert calls[2][-2:] == ["-r", str(repo_dir / "nova_core_requirements.txt")]


def test_ensure_runtime_reuses_existing_runtime_without_network_tool_upgrade(tmp_path: Path) -> None:
    from nova.bootstrap import ensure_runtime, runtime_python_path, runtime_root

    calls: list[list[str]] = []
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "requirements.txt").write_text("fastapi\n", encoding="utf-8")

    runtime_python = runtime_python_path(runtime_root(tmp_path))
    runtime_python.parent.mkdir(parents=True, exist_ok=True)
    runtime_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    def fake_run(command: list[str], **_: object) -> None:
        calls.append(command)
        if command[:4] == [str(runtime_python), "-m", "pip", "install"] and "--upgrade" in command:
            raise subprocess.CalledProcessError(1, command)

    ensure_runtime(
        repo_dir=repo_dir,
        home_dir=tmp_path,
        python_bin="/usr/bin/python3",
        command_runner=fake_run,
    )

    assert not any(command[:4] == [str(runtime_python), "-m", "pip", "install"] and "--upgrade" in command for command in calls)
    assert any(command[-2:] == ["-r", str(repo_dir / "requirements.txt")] for command in calls)


def test_ensure_runtime_repairs_incomplete_runtime_even_when_state_matches(tmp_path: Path, monkeypatch) -> None:
    from nova.bootstrap import ensure_runtime, runtime_python_path, runtime_root, runtime_state_path

    calls: list[list[str]] = []
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "nova_core_requirements.txt").write_text("pydantic\n", encoding="utf-8")

    runtime_python = runtime_python_path(runtime_root(tmp_path))
    runtime_python.parent.mkdir(parents=True, exist_ok=True)
    runtime_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    state_path = runtime_state_path(runtime_root(tmp_path))
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        '{"python_bin": "/usr/bin/python3", "repo_dir": "' + str(repo_dir) + '", "requirements_signature": "'
        + __import__("hashlib").sha256((repo_dir / "nova_core_requirements.txt").read_bytes()).hexdigest()
        + '"}',
        encoding="utf-8",
    )

    probe_results = iter([False, True])

    def fake_run(command: list[str], **_: object) -> None:
        calls.append(command)

    monkeypatch.setattr("nova.bootstrap._run_command", fake_run)
    monkeypatch.setattr("nova.bootstrap._runtime_is_healthy", lambda _runtime_python: False)
    monkeypatch.setattr("nova.bootstrap._probe_command", lambda _command: next(probe_results))

    ensure_runtime(
        repo_dir=repo_dir,
        home_dir=tmp_path,
        python_bin="/usr/bin/python3",
    )

    assert calls[0] == [str(runtime_python), "-m", "ensurepip", "--upgrade"]
    assert any(command[:4] == [str(runtime_python), "-m", "pip", "install"] for command in calls)


def test_select_bin_dir_defaults_to_canonical_nova_bin(tmp_path: Path) -> None:
    from nova.bootstrap import select_bin_dir

    selected = select_bin_dir(home_dir=tmp_path)

    assert selected == tmp_path / ".nova" / "bin"


def test_ensure_shell_path_persists_wrapper_dir_once(tmp_path: Path) -> None:
    from nova.bootstrap import ensure_shell_path

    bashrc = tmp_path / ".bashrc"
    profile = tmp_path / ".profile"
    bashrc.write_text("# bash\n", encoding="utf-8")
    profile.write_text("# existing\n", encoding="utf-8")
    bin_dir = tmp_path / ".nova" / "bin"

    ensure_shell_path(bin_dir, home_dir=tmp_path, path_value="/usr/bin")
    ensure_shell_path(bin_dir, home_dir=tmp_path, path_value="/usr/bin")

    profile_content = profile.read_text(encoding="utf-8")
    bash_content = bashrc.read_text(encoding="utf-8")
    assert 'export PATH="' in profile_content
    assert 'export PATH="' in bash_content
    assert profile_content.count(str(bin_dir)) == 1
    assert bash_content.count(str(bin_dir)) == 1


def test_run_command_retries_without_cwd_when_process_launch_fails() -> None:
    from nova.bootstrap import _run_command

    calls: list[tuple[list[str], str | None]] = []

    def fake_run(command: list[str], cwd: str | None = None, check: bool = True, text: bool = True):
        calls.append((command, cwd))
        if cwd is not None:
            raise FileNotFoundError("cwd not reachable")
        return None

    with mock.patch("subprocess.run", side_effect=fake_run):
        _run_command(["python3", "-V"], cwd=Path("/tmp/missing-cwd"))

    assert calls == [
        (["python3", "-V"], "/tmp/missing-cwd"),
        (["python3", "-V"], None),
    ]


def test_command_can_skip_runtime_for_help_but_not_default_start_invocation() -> None:
    from nova.bootstrap import command_can_skip_runtime

    assert not command_can_skip_runtime([])
    assert command_can_skip_runtime(["Help"])
    assert command_can_skip_runtime(["--help"])
    assert command_can_skip_runtime(["skill", "install", "--agent", "codex"])
    assert not command_can_skip_runtime(["start"])


def test_exec_nova_uses_host_python_for_lightweight_commands(tmp_path: Path) -> None:
    from nova.bootstrap import exec_nova

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "nova.py").write_text("print('ok')\n", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_run(command, check=False):
        calls.append(command)
        class Result:
            returncode = 0
        return Result()

    with mock.patch("subprocess.run", side_effect=fake_run), mock.patch("nova.bootstrap.ensure_runtime") as ensure_runtime:
        rc = exec_nova(repo_dir, ["Help"], python_bin="/usr/bin/python3")

    assert rc == 0
    assert calls == [["/usr/bin/python3", str(repo_dir / "nova.py"), "Help"]]
    ensure_runtime.assert_not_called()
