"""Formatting helpers for CLI and status output."""

from __future__ import annotations

from datetime import timedelta

from nova.constants import NOVA_ASCII_LOGO, NOVA_BUILD, NOVA_NAME


def _boxed(lines: list[str], *, width: int = 72) -> str:
    inner_width = max(width, max(len(line) for line in lines))
    top = "╔" + ("═" * (inner_width + 2)) + "╗"
    divider = "╠" + ("═" * (inner_width + 2)) + "╣"
    bottom = "╚" + ("═" * (inner_width + 2)) + "╝"
    body = [f"║ {line.ljust(inner_width)} ║" for line in lines]
    return "\n".join([top, *body[:11], divider, *body[11:], bottom])


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

    resolved_build = build or NOVA_BUILD.title()
    logo_lines = NOVA_ASCII_LOGO.strip("\n").splitlines()
    lines = [
        "",
        *logo_lines,
        "",
        f"      {NOVA_NAME} v{version} ({resolved_build})",
        "     Operator control plane for local AI agents",
        "",
        f"  Dashboard:   {dashboard_url}",
        f"  API Server:  {api_url}",
        f"  Bridge:      {bridge_url}",
        f"  API Docs:    {docs_url}",
        "  Status:      All systems operational ✓",
    ]
    return _boxed(lines, width=78)


def launch_banner(*, dashboard_url: str, version: str) -> str:
    """Return the immediate boot banner shown before the runtime is ready."""

    lines = [
        "",
        "                 NOVA OS BOOT",
        f"            Preparing operator runtime v{version}",
        "",
        f"  Dashboard target: {dashboard_url}",
        "  Runtime:          API + bridge + dashboard",
        "  Mode:             local operator control plane",
        "  Next:             services will come online and open when ready",
    ]
    return _boxed(lines, width=78)


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

    uptime_label = human_duration(uptime_seconds) if uptime_seconds is not None else "unknown"
    agent_label = str(active_agents) if active_agents is not None else "unknown"
    lines = [
        "",
        "                NOVA OS ONLINE",
        f"         Connected to operator runtime v{version}",
        "",
        f"  Dashboard:   {dashboard_url}",
        f"  API Server:  {api_url}",
        f"  Bridge:      {bridge_url}",
        f"  API Docs:    {docs_url}",
        f"  Agents:      {agent_label}",
        f"  Uptime:      {uptime_label}",
        "  Status:      Existing runtime already active ✓",
    ]
    return _boxed(lines, width=78)


def command_launchpad() -> str:
    """Return the human-facing command overview shown by `nova help`."""

    lines = [
        "",
        "             NOVA COMMAND LAUNCHPAD",
        "      Unified runtime, dashboard, discovery, governance",
        "",
        "  Start",
        "  nova                            Start Nova and open the dashboard",
        "  nova start                      Explicit runtime start",
        "  nova commands                   Show this launchpad",
        "  nova serve --api-only           API only, no SPA fallback",
        "",
        "  Discover",
        "  nova discover --json            Inspect repos, terminals, toolchains, agents",
        "  nova agents list                Show governed and discovered agents",
        "",
        "  Govern",
        "  nova connect <agent_key> --cannot-do \"rm -rf\"",
        "  nova validate --agent <agent> --action terminal.command --payload '{...}'",
        "  nova stream --agent <agent>     Follow evaluation history",
        "",
        "  Extend",
        "  nova skill install --agent codex",
        "  nova skill install --agent gemini",
        "  nova skill install --agent opencode",
        "",
        "  Operate",
        "  nova auth status | login | logout",
        "  nova ledger verify              Verify audit integrity",
        "  nova gateway status             Check provider routing",
    ]
    return _boxed(lines, width=88)


def human_duration(seconds: float) -> str:
    """Format seconds as a short human-readable duration."""

    return str(timedelta(seconds=int(seconds)))
