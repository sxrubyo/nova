"""Host inventory discovery regressions."""

from __future__ import annotations

from pathlib import Path

from nova.discovery.scanner import SystemScanner


def test_host_inventory_reports_repositories_and_codex_context(tmp_path: Path, monkeypatch) -> None:
    repo_dir = tmp_path / "nova-os"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    (repo_dir / ".codex").mkdir()
    (repo_dir / "pyproject.toml").write_text("[project]\nname = 'nova-os'\n", encoding="utf-8")
    (repo_dir / "package.json").write_text('{"name":"nova-os"}\n', encoding="utf-8")

    scanner = SystemScanner()
    monkeypatch.setattr(
        scanner,
        "_scan_terminal_processes",
        lambda repositories=None: [
            {
                "pid": 4242,
                "name": "bash",
                "cwd": str(repo_dir),
                "repo_path": str(repo_dir),
                "repo_name": "nova-os",
                "has_codex_context": True,
            }
        ],
    )
    monkeypatch.setattr(
        scanner,
        "_scan_tooling",
        lambda: [
            {"key": "git", "label": "Git", "category": "vcs", "installed": True, "version": "git version 2.43.0"},
            {"key": "python", "label": "Python", "category": "runtime", "installed": True, "version": "Python 3.11.9"},
            {"key": "node", "label": "Node.js", "category": "runtime", "installed": False, "version": None},
            {"key": "npm", "label": "npm", "category": "runtime", "installed": False, "version": None},
            {"key": "rg", "label": "ripgrep", "category": "automation", "installed": False, "version": None},
            {"key": "codex", "label": "Codex CLI", "category": "assistant", "installed": True, "version": "codex 1.0"},
        ],
    )
    monkeypatch.setattr(scanner, "_host_profile", lambda: {"platform": "linux", "package_manager": {"name": "apt-get", "auto_install_supported": True}})

    inventory = scanner.host_inventory(roots=[tmp_path])

    assert inventory["summary"]["repositories"] == 1
    assert inventory["summary"]["terminals"] == 1
    assert inventory["summary"]["active_repositories"] == 1
    assert "has_codex_home" in inventory["signals"]
    assert inventory["repositories"][0]["path"] == str(repo_dir)
    assert inventory["repositories"][0]["has_codex"] is True
    assert inventory["repositories"][0]["is_active"] is True
    assert set(inventory["repositories"][0]["ecosystems"]) == {"node", "python"}
    assert inventory["terminals"][0]["repo_path"] == str(repo_dir)
    assert inventory["recommended_installs"][0]["tool"] == "node"
    assert inventory["recommended_installs"][0]["install_command"].startswith("sudo apt-get install -y")


def test_scan_tooling_includes_supported_assistant_clis(monkeypatch) -> None:
    scanner = SystemScanner()
    binaries = {
        "codex": "/usr/bin/codex",
        "opencode": "/usr/bin/opencode",
    }
    versions = {
        "codex": "codex-cli 0.125.0",
        "opencode": "1.14.22",
    }

    monkeypatch.setattr(
        scanner,
        "_resolve_tool_binary",
        lambda commands: binaries.get(commands[0]),
    )
    monkeypatch.setattr(
        scanner,
        "_tool_version",
        lambda key, resolved: versions.get(key),
    )

    tooling = scanner._scan_tooling()
    by_key = {item["key"]: item for item in tooling}

    assert by_key["codex"]["installed"] is True
    assert by_key["opencode"]["installed"] is True
    assert by_key["gemini"]["installed"] is False
    assert by_key["claude"]["installed"] is False
