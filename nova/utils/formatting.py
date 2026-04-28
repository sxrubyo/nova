"""Formatting helpers for branded Nova CLI surfaces."""

from __future__ import annotations

import os
import shutil
import sys
import textwrap
from datetime import datetime
from datetime import timedelta, timezone

from nova.constants import NOVA_BUILD, NOVA_CODENAME, NOVA_NAME, NOVA_STARBURST_LINES, NOVA_VERSION

NOVA_TAGLINES = (
    "The missing layer in your AI stack.",
    "Intelligence with limits. Actions with proof.",
    "Built for scale. Designed for trust.",
    "What stands between your agent and the world.",
    "Sleep well. Your agents are supervised.",
)


def _supports_color() -> bool:
    return sys.stdout.isatty() or bool(os.getenv("FORCE_COLOR"))


def _paint(text: str, code: str, *, bold: bool = False) -> str:
    if not _supports_color():
        return text
    prefix = "\033[1m" if bold else ""
    return f"{prefix}\033[{code}m{text}\033[0m"


def primary(text: str, *, bold: bool = False) -> str:
    return _paint(text, "38;5;15", bold=bold)


def muted(text: str) -> str:
    return _paint(text, "38;5;244")


def accent(text: str, *, bold: bool = False) -> str:
    return _paint(text, "38;5;221", bold=bold)


def warm(text: str, *, bold: bool = False) -> str:
    return _paint(text, "38;5;179", bold=bold)


def _rotating_tagline() -> str:
    day_index = datetime.now(timezone.utc).toordinal() % len(NOVA_TAGLINES)
    return NOVA_TAGLINES[day_index]


def _terminal_width(default: int = 72) -> int:
    try:
        return shutil.get_terminal_size((default, 24)).columns
    except Exception:
        return default


def _content_width(default: int = 72, *, minimum: int = 42) -> int:
    return max(minimum, min(default, _terminal_width(default)))


def _divider(width: int) -> str:
    return muted("  " + ("─" * max(34, min(width - 2, 62))))


def _wrap_rows(rows: list[str], *, width: int, indent: str = "  ") -> list[str]:
    rendered: list[str] = []
    available = max(24, width - len(indent))
    for row in rows:
        if not row:
            rendered.append("")
            continue
        wrapped = textwrap.wrap(
            row,
            width=available,
            break_long_words=False,
            break_on_hyphens=False,
        )
        rendered.extend(f"{indent}{line}" for line in (wrapped or [row[:available]]))
    return rendered


def _brand_lines(*, version: str, tagline: str) -> list[str]:
    return [
        "",
        *(accent(line) for line in NOVA_STARBURST_LINES),
        "",
        accent("           N  O  V  A", bold=True),
        muted(f"           ·  v{version} {NOVA_CODENAME}  ·"),
        "",
        muted(f"  {tagline}"),
        accent("  ✦", bold=True) + " " + muted("Constellation · Enterprise Edition"),
    ]


def compact_cli_banner(*, title: str, subtitle: str | None = None, version: str = NOVA_VERSION) -> str:
    """Return the branded operator header used by secondary CLI commands."""

    width = _content_width(74)
    lines = _brand_lines(version=version, tagline=_rotating_tagline())
    lines.append(_divider(width))
    lines.append("")
    lines.append("  " + accent("✦", bold=True) + "  " + primary(title, bold=True))
    if subtitle:
        lines.append("    " + muted(subtitle))
    return "\n".join(lines)


def _section(title: str, rows: list[str], *, width: int) -> list[str]:
    lines = [
        "  " + warm(title, bold=True),
        _divider(width),
        "",
    ]
    lines.extend(_wrap_rows(rows, width=width))
    return lines


def _status_row(label: str, value: str) -> str:
    return f"{label:<13}{value}"


def startup_banner(
    *,
    api_url: str,
    dashboard_url: str,
    docs_url: str,
    bridge_url: str,
    version: str,
    build: str | None = None,
) -> str:
    """Return the Nova runtime startup banner."""

    resolved_build = (build or NOVA_BUILD).title()
    width = _content_width(74)
    lines = _brand_lines(version=version, tagline="Governance at machine speed.")
    lines.append(_divider(width))
    lines.append("")
    lines.extend(
        _section(
            f"{NOVA_NAME.upper()} ONLINE",
            [
                _status_row("Build:", resolved_build),
                _status_row("Dashboard:", dashboard_url),
                _status_row("API Server:", api_url),
                _status_row("Bridge:", bridge_url),
                _status_row("API Docs:", docs_url),
                _status_row("Status:", "All systems operational ✓"),
            ],
            width=width,
        )
    )
    return "\n".join(lines)


def launch_banner(*, dashboard_url: str, version: str) -> str:
    """Return the immediate boot banner shown before the runtime is ready."""

    width = _content_width(74)
    lines = _brand_lines(version=version, tagline="Governance at machine speed.")
    lines.append(_divider(width))
    lines.append("")
    lines.extend(
        _section(
            f"{NOVA_NAME.upper()} BOOT",
            [
                _status_row("Dashboard:", dashboard_url),
                _status_row("Runtime:", "API + bridge + dashboard"),
                _status_row("Mode:", "local operator control plane"),
                _status_row("Next:", "services will come online and open when ready"),
            ],
            width=width,
        )
    )
    return "\n".join(lines)


def existing_runtime_banner(
    *,
    api_url: str,
    dashboard_url: str,
    docs_url: str,
    bridge_url: str,
    version: str,
    active_agents: int | None = None,
    uptime_seconds: float | None = None,
) -> str:
    """Return the operator-facing banner when Nova is already online."""

    width = _content_width(74)
    uptime_label = human_duration(uptime_seconds) if uptime_seconds is not None else "unknown"
    agent_label = str(active_agents) if active_agents is not None else "unknown"
    lines = _brand_lines(version=version, tagline="Governance at machine speed.")
    lines.append(_divider(width))
    lines.append("")
    lines.extend(
        _section(
            f"{NOVA_NAME.upper()} ONLINE",
            [
                _status_row("Dashboard:", dashboard_url),
                _status_row("API Server:", api_url),
                _status_row("Bridge:", bridge_url),
                _status_row("API Docs:", docs_url),
                _status_row("Agents:", agent_label),
                _status_row("Uptime:", uptime_label),
                _status_row("Status:", "Existing runtime already active ✓"),
            ],
            width=width,
        )
    )
    return "\n".join(lines)


def command_launchpad(*, width: int = 74) -> str:
    """Return the human-facing command overview shown by `nova help`."""

    resolved_width = _content_width(width)
    lines = [compact_cli_banner(title="Nova Commands", subtitle="Common operator paths for runtime, discovery and governance.")]
    lines.extend(
        _section(
            "GETTING STARTED",
            [
                "nova                    Abrir la superficie principal de Nova",
                "nova init               First-run setup wizard",
                "nova boot               Start Nova Core + connect all agents",
                "nova guard              Protect all your AI agents in one command",
                "nova rule \"<text>\"      Add a governance rule instantly",
                "nova status             System health and metrics",
                "nova launchpad          Guided operator entrypoint",
                "nova config             Interactive settings hub",
                "nova workspace          Workspace info, plan, quota",
            ],
            width=resolved_width,
        )
    )
    lines.extend(
        _section(
            "AGENTS",
            [
                "nova agent create       Create agent - NL / template / manual",
                "nova agent list         List all agents",
                "nova agent edit         Edit rules, description, policy",
                "nova agent history      View version history of rules",
                "nova setup              Opinionated setup for known agent types",
                "nova connect            Connect Nova Core to a running agent",
            ],
            width=resolved_width,
        )
    )
    lines.extend(
        _section(
            "POLICIES",
            [
                "nova policy             List policy templates",
                "nova policy create      Create reusable rule set",
                "nova policy view <id>   View a specific policy",
                "nova policy edit <id>   Edit a policy",
                "nova policy delete      Delete a policy",
            ],
            width=resolved_width,
        )
    )
    lines.extend(
        _section(
            "VALIDATION",
            [
                "nova validate           Validate an action",
                "nova validate explain   Deep AI explanation of the decision",
                "nova validate batch     Validate up to 20 actions in parallel",
                "nova simulate           Test policy without creating token/ledger",
                "nova test               Dry-run validation",
            ],
            width=resolved_width,
        )
    )
    lines.extend(
        _section(
            "MEMORY",
            [
                "nova memory save        Store agent context",
                "nova memory list        View agent memories",
                "nova memory search      Semantic search across memories",
                "nova memory update      Edit an existing memory",
            ],
            width=resolved_width,
        )
    )
    lines.extend(
        _section(
            "LEDGER",
            [
                "nova ledger             View action history",
                "nova verify             Check chain integrity",
                "nova watch              Live stream entries",
                "nova export             Export to JSON/CSV",
                "nova audit              Generate audit report",
            ],
            width=resolved_width,
        )
    )
    lines.extend(
        _section(
            "API KEYS",
            [
                "nova keys               List saved keys",
                "nova keys create        Generate new key",
                "nova keys use           Switch active key",
            ],
            width=resolved_width,
        )
    )
    lines.extend(
        _section(
            "SKILLS",
            [
                "nova skill              Browse catalog (↑↓)",
                "nova skill add <name>   Install a skill",
                "nova skill info <name>  View skill details",
            ],
            width=resolved_width,
        )
    )
    lines.extend(
        _section(
            "GOVERNANCE INTEGRATIONS",
            [
                "nova rules              List, manage & test rules",
                "nova rules create       Interactive rule builder",
                "nova rules test         Test a rule against a sample action",
                "nova run                Wrap any CLI command with Nova validation",
                "nova shield             HTTP proxy - intercept & validate every request",
                "nova protect            Attach to a live HTTP agent",
                "",
                "nova discover --json    Escanear repos, terminales, toolchains y agentes",
                "nova agents list        Ver agentes gobernados y descubiertos",
                "nova connect <agent> --cannot-do \"rm -rf\"",
                "nova validate --agent <agent> --action terminal.command --payload '{...}'",
                "nova stream --agent <agent>  Seguir evaluaciones en vivo",
                "nova scout              Security scan - detect misconfigurations",
            ],
            width=resolved_width,
        )
    )
    lines.extend(
        _section(
            "TOOLS & SYSTEM",
            [
                "nova doctor             Diagnose & auto-repair common issues",
                "nova mcp export         Export config as MCP-compatible manifest",
                "nova mcp import         Import MCP tool definitions",
                "nova chat               Chat with the Nova governance AI",
                "nova anomalies          View detected behavioral anomalies",
                "nova stream             Live-stream raw validation events",
                "nova benchmark          Measure validation latency & throughput",
            ],
            width=resolved_width,
        )
    )
    lines.extend(
        _section(
            "STATS",
            [
                "nova stats              Analytics overview",
                "nova stats agents       Per-agent breakdown",
                "nova stats hourly       Activity heatmap by hour",
                "nova stats risk         Risk profile per agent",
                "nova stats timeline     Hour-by-hour timeline",
                "nova stats anomalies    Detected behavioral anomalies",
            ],
            width=resolved_width,
        )
    )
    lines.extend(
        _section(
            "SYSTEM",
            [
                "nova auth status        Current operator session status",
                "nova auth login         Sign in to the active workspace",
                "nova auth logout        Clear the saved local session",
                "nova gateway status     Revisar routing de proveedores",
                "nova sync               Process offline queue",
                "nova seed               Load demo data",
                "nova alerts             View pending alerts",
            ],
            width=resolved_width,
        )
    )
    lines.extend(
        _section(
            "ALIASES",
            [
                "s → status  v → validate  a → agent  c → config  l → ledger",
                "w → watch  r → rules  st → stats  pol → policy  sim → simulate",
            ],
            width=resolved_width,
        )
    )
    return "\n".join(lines)


def operator_launchpad_header(*, version: str) -> str:
    """Return the branded launchpad header shown by `nova` and `nova launchpad`."""

    width = _content_width(74)
    lines = [compact_cli_banner(title="Operator Launchpad", subtitle="Elige la siguiente acción sin salir de la terminal.", version=version)]
    lines.extend(
        _section(
            "OPERATOR LAUNCHPAD",
            [
                "Nova mantiene navegación por flechas aquí; la referencia completa vive en `nova commands`.",
            ],
            width=width,
        )
    )
    return "\n".join(lines)


def human_duration(seconds: float) -> str:
    """Format seconds as a short human-readable duration."""

    return str(timedelta(seconds=int(seconds)))
