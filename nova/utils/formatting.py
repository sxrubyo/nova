"""Formatting helpers for branded Nova CLI surfaces."""

from __future__ import annotations

import shutil
import textwrap
from datetime import timedelta

from nova.constants import NOVA_BUILD, NOVA_CODENAME, NOVA_NAME, NOVA_STARBURST_LINES, NOVA_VERSION


def _terminal_width(default: int = 72) -> int:
    try:
        return shutil.get_terminal_size((default, 24)).columns
    except Exception:
        return default


def _content_width(default: int = 72, *, minimum: int = 42) -> int:
    return max(minimum, min(default, _terminal_width(default)))


def _divider(width: int) -> str:
    return "  " + ("─" * max(34, min(width - 2, 42)))


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
        *NOVA_STARBURST_LINES,
        "",
        "           N  O  V  A",
        f"           ·  v{version} {NOVA_CODENAME}  ·",
        "",
        f"  {tagline}",
    ]


def _section(title: str, rows: list[str], *, width: int) -> list[str]:
    lines = [
        f"  {title}",
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
    lines = _brand_lines(version=NOVA_VERSION, tagline="Governance at machine speed.")
    lines.append(_divider(resolved_width))
    lines.append("")
    lines.extend(
        _section(
            "NOVA COMMAND LAUNCHPAD",
            [
                "Common operator paths for runtime, discovery and governance.",
                "",
                "START",
                "nova                    Abrir la superficie principal de Nova",
                "nova start              Arrancar runtime explícitamente",
                "nova launchpad          Abrir el menú operator con flechas",
                "nova serve --api-only   Exponer solo la API sin SPA",
                "",
                "DISCOVER",
                "nova discover --json    Escanear repos, terminales, toolchains y agentes",
                "nova agents list        Ver agentes gobernados y descubiertos",
                "",
                "GOVERN",
                "nova connect <agent> --cannot-do \"rm -rf\"",
                "nova validate --agent <agent> --action terminal.command --payload '{...}'",
                "nova stream --agent <agent>  Seguir evaluaciones en vivo",
                "",
                "EXTEND",
                "nova skill install --agent codex",
                "nova skill install --agent gemini",
                "nova skill install --agent opencode",
                "",
                "OPERATE",
                "nova auth status | login | logout",
                "nova ledger verify      Verificar integridad del ledger",
                "nova gateway status     Revisar routing de proveedores",
            ],
            width=resolved_width,
        )
    )
    return "\n".join(lines)


def operator_launchpad_header(*, version: str) -> str:
    """Return the branded launchpad header shown by `nova` and `nova launchpad`."""

    width = _content_width(74)
    lines = _brand_lines(version=version, tagline="Governance at machine speed.")
    lines.append(_divider(width))
    lines.append("")
    lines.extend(
        _section(
            "OPERATOR LAUNCHPAD",
            [
                "Elige la siguiente acción sin salir de la terminal.",
                "Nova mantiene navegación por flechas aquí; la referencia completa vive en `nova commands`.",
            ],
            width=width,
        )
    )
    return "\n".join(lines)


def human_duration(seconds: float) -> str:
    """Format seconds as a short human-readable duration."""

    return str(timedelta(seconds=int(seconds)))
