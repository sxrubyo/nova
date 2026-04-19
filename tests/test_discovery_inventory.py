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

    inventory = scanner.host_inventory(roots=[tmp_path])

    assert inventory["summary"]["repositories"] == 1
    assert inventory["summary"]["terminals"] == 1
    assert "has_codex_home" in inventory["signals"]
    assert inventory["repositories"][0]["path"] == str(repo_dir)
    assert inventory["repositories"][0]["has_codex"] is True
    assert set(inventory["repositories"][0]["ecosystems"]) == {"node", "python"}
    assert inventory["terminals"][0]["repo_path"] == str(repo_dir)
