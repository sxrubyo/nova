from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from unittest import mock
from pathlib import Path

import pytest

from nova.utils.formatting import command_launchpad, existing_runtime_banner, startup_banner


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("nova_cli_module", ROOT / "nova.py")
assert SPEC and SPEC.loader
NOVA_CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NOVA_CLI)


def test_help_command_prints_launchpad() -> None:
    result = subprocess.run(
        [sys.executable, "nova.py", "help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Enterprise-grade governance infrastructure for AI agents." in result.stdout
    assert "GETTING STARTED" in result.stdout
    assert "nova boot" in result.stdout


def test_start_subcommand_is_registered() -> None:
    result = subprocess.run(
        [sys.executable, "nova.py", "start", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "usage: nova start" in result.stdout
    assert "--bridge-port" in result.stdout


def test_empty_cli_defaults_to_start() -> None:
    args = NOVA_CLI.parse_cli_args([])

    assert args.command == "start"
    assert args.no_open_browser is False


def test_empty_cli_routes_to_modern_start(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, object] = {}

    async def fake_run_async(args, raw_args=None):
        observed["command"] = args.command
        observed["raw_args"] = raw_args

    def fail_legacy(argv: list[str]) -> None:
        raise AssertionError(f"legacy CLI should not be used for empty argv: {argv}")

    monkeypatch.setattr(NOVA_CLI, "run_async", fake_run_async)
    monkeypatch.setattr(NOVA_CLI, "_run_legacy_cli", fail_legacy)

    NOVA_CLI.main([])

    assert observed == {"command": "start", "raw_args": []}


def test_top_level_help_flag_routes_to_help_command() -> None:
    args = NOVA_CLI.parse_cli_args(["--help"])

    assert args.command == "help"


def test_commands_alias_routes_to_help_command() -> None:
    args = NOVA_CLI.parse_cli_args(["commands"])

    assert args.command == "help"


def test_commands_alias_dispatches_to_modern_launchpad() -> None:
    result = subprocess.run(
        [sys.executable, "nova.py", "commands"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Enterprise-grade governance infrastructure for AI agents." in result.stdout
    assert "GOVERNANCE INTEGRATIONS" in result.stdout
    assert "nova guard" in result.stdout


def test_help_command_is_case_insensitive_for_primary_alias() -> None:
    args = NOVA_CLI.parse_cli_args(["Help"])

    assert args.command == "help"


def test_platform_bootstrap_is_skipped_for_lightweight_commands() -> None:
    assert NOVA_CLI.command_requires_platform_bootstrap("help") is False
    assert NOVA_CLI.command_requires_platform_bootstrap("version") is False
    assert NOVA_CLI.command_requires_platform_bootstrap("skill") is False
    assert NOVA_CLI.command_requires_platform_bootstrap("auth") is False


def test_platform_bootstrap_runs_for_runtime_commands() -> None:
    assert NOVA_CLI.command_requires_platform_bootstrap("start") is True
    assert NOVA_CLI.command_requires_platform_bootstrap("discover") is True


def test_legacy_dispatch_identifies_legacy_and_modern_routes() -> None:
    assert NOVA_CLI._legacy_dispatch_argv([]) is None
    assert NOVA_CLI._legacy_dispatch_argv(["help"]) == ["help"]
    assert NOVA_CLI._legacy_dispatch_argv(["commands"]) == ["help"]
    assert NOVA_CLI._legacy_dispatch_argv(["launchpad"]) is None
    assert NOVA_CLI._legacy_dispatch_argv(["boot"]) == ["boot"]
    assert NOVA_CLI._legacy_dispatch_argv(["start"]) is None
    assert NOVA_CLI._legacy_dispatch_argv(["discover"]) is None


def test_attempt_bootstrap_reexec_recovers_missing_runtime_dependency(monkeypatch) -> None:
    monkeypatch.delenv(NOVA_CLI.BOOTSTRAP_RECOVERY_FLAG, raising=False)

    with mock.patch("nova.bootstrap.exec_nova", return_value=0) as exec_nova:
        with pytest.raises(SystemExit) as exc_info:
            NOVA_CLI._attempt_bootstrap_reexec(["start"], ModuleNotFoundError("missing", name="pydantic"))

    assert exc_info.value.code == 0
    exec_nova.assert_called_once_with(ROOT, ["start"], python_bin=sys.executable)
    assert os.environ[NOVA_CLI.BOOTSTRAP_RECOVERY_FLAG] == "1"


def test_commands_alias_prints_launchpad() -> None:
    result = subprocess.run(
        [sys.executable, "nova.py", "commands"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Constellation · Enterprise Edition" in result.stdout
    assert "nova skill" in result.stdout


def test_launchpad_action_argv_stays_disabled_without_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOVA_NO_INTERACTIVE", "1")

    assert NOVA_CLI._launchpad_action_argv("help") is None


def test_command_launchpad_lists_primary_workflows() -> None:
    launchpad = command_launchpad()

    assert "nova" in launchpad
    assert "nova discover --json" in launchpad
    assert "nova skill install --agent codex" in launchpad
    assert "nova validate" in launchpad


def test_startup_banner_surfaces_dashboard_and_docs() -> None:
    banner = startup_banner(
        api_url="http://127.0.0.1:9800",
        dashboard_url="http://127.0.0.1:9800/",
        docs_url="http://127.0.0.1:9800/api/docs",
        bridge_url="ws://127.0.0.1:9700",
        version="4.0.7",
    )

    assert "Dashboard:" in banner
    assert "http://127.0.0.1:9800/" in banner
    assert "API Docs:" in banner


def test_existing_runtime_banner_surfaces_attach_state() -> None:
    banner = existing_runtime_banner(
        api_url="http://127.0.0.1:9800",
        dashboard_url="http://127.0.0.1:9800/",
        docs_url="http://127.0.0.1:9800/api/docs",
        bridge_url="ws://127.0.0.1:9700",
        version="4.0.7",
        active_agents=3,
        uptime_seconds=95,
    )

    assert "NOVA OS ONLINE" in banner
    assert "Existing runtime already active" in banner
    assert "Agents:" in banner


def test_discovery_tooling_rows_prioritize_assistant_clis() -> None:
    rows = NOVA_CLI._discovery_tooling_rows(
        [
            {"key": "git", "label": "Git", "category": "vcs", "installed": True, "version": "2.43"},
            {"key": "node", "label": "Node.js", "category": "runtime", "installed": True, "version": "22.0"},
            {"key": "opencode", "label": "OpenCode", "category": "assistant", "installed": True, "version": "1.14.22"},
            {"key": "codex", "label": "Codex CLI", "category": "assistant", "installed": True, "version": "0.125.0"},
        ],
        limit=4,
    )

    assert [item["key"] for item in rows] == ["codex", "opencode", "node", "git"]


def test_legacy_commands_do_not_get_blocked_by_missing_config() -> None:
    with tempfile.TemporaryDirectory() as tmp_home:
        config_result = subprocess.run(
            [sys.executable, str(ROOT / "nova.py"), "config"],
            cwd=ROOT,
            env={**os.environ, "HOME": tmp_home},
            input="10\n",
            capture_output=True,
            text=True,
            check=False,
        )

        assert config_result.returncode == 0, config_result.stderr
        assert "isn't configured yet" not in config_result.stdout
        assert "API key is not configured" in config_result.stdout

        boot_result = subprocess.run(
            [sys.executable, str(ROOT / "nova.py"), "boot"],
            cwd=ROOT,
            env={**os.environ, "HOME": tmp_home},
            capture_output=True,
            text=True,
            check=False,
        )

        assert boot_result.returncode == 0, boot_result.stderr
        assert "isn't configured yet" not in boot_result.stdout
        assert "Nova Boot" in boot_result.stdout


def test_guard_summary_no_longer_crashes_on_description_nameerror() -> None:
    with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp_cwd:
        result = subprocess.run(
            [sys.executable, str(ROOT / "nova.py"), "guard", "--path", ".env"],
            cwd=tmp_cwd,
            env={**os.environ, "HOME": tmp_home},
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        assert "name 'description' is not defined" not in result.stdout
        assert "Nova Guard active" in result.stdout
