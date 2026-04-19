from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run_skill_install(agent: str, home: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    return subprocess.run(
        [sys.executable, "nova.py", "skill", "install", "--agent", agent, "--json"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_skill_install_for_codex_writes_skill_bundle(tmp_path: Path) -> None:
    result = _run_skill_install("codex", tmp_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    skill_path = tmp_path / ".agents" / "skills" / "nova-governance" / "SKILL.md"
    metadata_path = tmp_path / ".agents" / "skills" / "nova-governance" / "agents" / "openai.yaml"

    assert payload["agent"] == "codex"
    assert skill_path.exists()
    assert metadata_path.exists()
    assert "nova discover --json" in skill_path.read_text(encoding="utf-8")


def test_skill_install_for_gemini_and_opencode_creates_bridge_docs(tmp_path: Path) -> None:
    gemini_result = _run_skill_install("gemini", tmp_path)
    opencode_result = _run_skill_install("opencode", tmp_path)

    assert gemini_result.returncode == 0, gemini_result.stderr
    assert opencode_result.returncode == 0, opencode_result.stderr

    gemini_skill = tmp_path / ".gemini" / "skills" / "nova-governance.md"
    gemini_index = tmp_path / ".gemini" / "GEMINI.md"
    opencode_skill = tmp_path / ".config" / "opencode" / "skills" / "nova-governance.md"
    opencode_index = tmp_path / ".config" / "opencode" / "AGENTS.md"

    assert gemini_skill.exists()
    assert opencode_skill.exists()
    assert "nova-governance.md" in gemini_index.read_text(encoding="utf-8")
    assert "nova-governance.md" in opencode_index.read_text(encoding="utf-8")
