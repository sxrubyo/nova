"""Install Nova governance skill bridges for local agent CLIs."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


SUPPORTED_AGENT_SKILL_TARGETS = ("codex", "gemini", "opencode")
SKILL_NAME = "nova-governance"
BRIDGE_MARKER = "<!-- nova-governance-bridge -->"


def source_skill_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[1]
    return root / "skills" / SKILL_NAME


def install_skill(agent: str, home: Path | None = None, repo_root: Path | None = None) -> dict[str, Any]:
    """Install the Nova governance skill bundle for the selected agent surface."""

    target = agent.lower()
    if target == "all":
        installs = [install_skill(agent_name, home=home, repo_root=repo_root) for agent_name in SUPPORTED_AGENT_SKILL_TARGETS]
        return {"agent": "all", "targets": installs}
    if target not in SUPPORTED_AGENT_SKILL_TARGETS:
        raise ValueError(f"unsupported skill target: {agent}")

    root = home or Path.home()
    source_dir = source_skill_dir(repo_root)
    if not source_dir.exists():
        raise FileNotFoundError(f"skill bundle not found at {source_dir}")

    if target == "codex":
        return _install_codex(source_dir, root)
    if target == "gemini":
        return _install_bridge_agent(
            source_dir=source_dir,
            agent="gemini",
            root=root,
            skill_doc=root / ".gemini" / "skills" / f"{SKILL_NAME}.md",
            index_doc=root / ".gemini" / "GEMINI.md",
        )
    return _install_bridge_agent(
        source_dir=source_dir,
        agent="opencode",
        root=root,
        skill_doc=root / ".config" / "opencode" / "skills" / f"{SKILL_NAME}.md",
        index_doc=root / ".config" / "opencode" / "AGENTS.md",
    )


def _install_codex(source_dir: Path, root: Path) -> dict[str, Any]:
    target_dir = root / ".agents" / "skills" / SKILL_NAME
    installed_files: list[str] = []
    for path in source_dir.rglob("*"):
        if path.is_dir():
            continue
        relative = path.relative_to(source_dir)
        destination = target_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        installed_files.append(str(destination))
    return {
        "agent": "codex",
        "mode": "native_skill",
        "skill_dir": str(target_dir),
        "installed_files": installed_files,
    }


def _install_bridge_agent(source_dir: Path, agent: str, root: Path, *, skill_doc: Path, index_doc: Path) -> dict[str, Any]:
    skill_doc.parent.mkdir(parents=True, exist_ok=True)
    rendered_skill = source_dir.joinpath("SKILL.md").read_text(encoding="utf-8")
    skill_doc.write_text(rendered_skill, encoding="utf-8")
    bridge_block = _bridge_block(agent=agent, skill_doc=skill_doc)
    _upsert_bridge(index_doc, bridge_block)
    return {
        "agent": agent,
        "mode": "instruction_bridge",
        "skill_doc": str(skill_doc),
        "index_doc": str(index_doc),
        "installed_files": [str(skill_doc), str(index_doc)],
    }


def _bridge_block(*, agent: str, skill_doc: Path) -> str:
    return (
        f"{BRIDGE_MARKER}\n"
        "## Nova Governance\n\n"
        f"Use `{skill_doc}` when you need Nova to discover local repositories, terminals, toolchains, "
        f"or connected agents before acting from {agent}. Route risky terminal or HTTP actions through "
        "`nova discover`, `nova connect`, and `nova validate` first.\n"
        f"{BRIDGE_MARKER}\n"
    )


def _upsert_bridge(index_doc: Path, bridge_block: str) -> None:
    current = index_doc.read_text(encoding="utf-8") if index_doc.exists() else ""
    if BRIDGE_MARKER in current:
        prefix, _, remainder = current.partition(BRIDGE_MARKER)
        _, _, suffix = remainder.partition(BRIDGE_MARKER)
        cleaned = f"{prefix.rstrip()}\n\n{suffix.lstrip()}".strip()
        current = f"{cleaned}\n" if cleaned else ""
    if current and not current.endswith("\n"):
        current += "\n"
    index_doc.parent.mkdir(parents=True, exist_ok=True)
    index_doc.write_text(f"{current}\n{bridge_block}".lstrip(), encoding="utf-8")
