"""Nova OS CLI entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import platform
import sys
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except ImportError:  # pragma: no cover - optional host fallback
    Console = None
    Panel = None
    Table = None


CLI_SESSION_PATH = Path.home() / ".nova" / "web_session.json"
CLI_COMMAND_ALIASES = {
    "command": "help",
    "commands": "help",
    "launchpad": "help",
    "lp": "help",
}
LIGHTWEIGHT_COMMANDS = {"help", "version", "skill", "auth"}
MODERN_RUNTIME_COMMANDS = {"start", "serve", "discover", "evaluate", "agents", "gateway", "auth", "skill"}
LEGACY_ALIAS_MAP = {
    "command": "help",
    "commands": "help",
    "launchpad": "launchpad",
    "lp": "launchpad",
}
BOOTSTRAP_RECOVERY_MODULES = {
    "pydantic",
    "pydantic_settings",
    "fastapi",
    "sqlalchemy",
    "aiosqlite",
    "asyncpg",
    "rich",
    "httpx",
    "click",
}
BOOTSTRAP_RECOVERY_FLAG = "NOVA_AUTO_BOOTSTRAP_REEXEC"


def _nova_version() -> str:
    from nova.constants import NOVA_VERSION

    return NOVA_VERSION


def _to_payload(value: Any) -> Any:
    from nova.api.dependencies import to_payload

    return to_payload(value)


def _platform_bootstrap() -> None:
    """Initialize portable runtime defaults before command execution."""

    try:
        from nova.db import init_db
        from nova.platform import PLATFORM

        if PLATFORM.db_engine == "sqlite":
            asyncio.run(init_db())
    except ImportError:
        pass


def command_requires_platform_bootstrap(command: str | None) -> bool:
    return bool(command) and command not in LIGHTWEIGHT_COMMANDS


def _legacy_cli_path() -> Path:
    return Path(__file__).resolve().parent / "legacy" / "nova_cli_legacy.py"


def _legacy_dispatch_argv(raw_args: list[str]) -> list[str] | None:
    if not raw_args:
        return []

    first = raw_args[0]
    if first in ("-h", "--help"):
        return ["help"]
    if first.startswith("-"):
        return None

    normalized = first.lower()
    if normalized in LEGACY_ALIAS_MAP:
        return [LEGACY_ALIAS_MAP[normalized], *raw_args[1:]]
    if normalized not in MODERN_RUNTIME_COMMANDS:
        return [normalized, *raw_args[1:]]
    return None


def _run_legacy_cli(argv: list[str]) -> None:
    legacy_path = _legacy_cli_path()
    spec = importlib.util.spec_from_file_location("nova_legacy_cli", legacy_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Legacy CLI not found at {legacy_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_argv = sys.argv[:]
    try:
        sys.argv = [original_argv[0], *argv]
        module.main()
    finally:
        sys.argv = original_argv


def _attempt_bootstrap_reexec(raw_args: list[str], exc: ModuleNotFoundError) -> None:
    missing_module = getattr(exc, "name", "") or ""
    if missing_module not in BOOTSTRAP_RECOVERY_MODULES:
        raise exc
    if os.environ.get(BOOTSTRAP_RECOVERY_FLAG) == "1":
        raise exc
    print(
        f"[nova] Missing runtime dependency '{missing_module}'. Repairing Nova runtime and retrying...",
        file=sys.stderr,
        flush=True,
    )
    from nova.bootstrap import exec_nova

    os.environ[BOOTSTRAP_RECOVERY_FLAG] = "1"
    raise SystemExit(
        exec_nova(
            Path(__file__).resolve().parent,
            raw_args,
            python_bin=sys.executable,
        )
    ) from exc


def _resolve_api_url(api_url: str | None) -> str:
    return (api_url or os.getenv("NOVA_API_URL") or os.getenv("NOVA_SERVER_URL") or "http://127.0.0.1:8000").rstrip("/")


def _cli_session_headers(api_url: str | None = None) -> dict[str, str]:
    if not CLI_SESSION_PATH.exists():
        return {}
    try:
        session = json.loads(CLI_SESSION_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    cookie_name = session.get("cookie_name")
    cookie_value = session.get("cookie_value")
    stored_api_url = str(session.get("api_url") or "").rstrip("/")
    requested_api_url = _resolve_api_url(api_url)
    if not cookie_name or not cookie_value:
        return {}
    if stored_api_url and stored_api_url != requested_api_url:
        return {}
    return {"Cookie": f"{cookie_name}={cookie_value}"}


def _clear_cli_session() -> None:
    if CLI_SESSION_PATH.exists():
        CLI_SESSION_PATH.unlink()


def _extract_session_cookie(headers: Any) -> tuple[str, str] | None:
    cookie_headers = list(headers.get_all("Set-Cookie") or [])
    preferred: tuple[str, str] | None = None
    for raw_cookie in cookie_headers:
        jar = SimpleCookie()
        jar.load(raw_cookie)
        for key, morsel in jar.items():
            candidate = (key, morsel.value)
            if key == "nova_session":
                return candidate
            preferred = preferred or candidate
    return preferred


def _persist_cli_session(api_url: str, headers: Any, payload: dict[str, Any]) -> None:
    cookie = _extract_session_cookie(headers)
    if cookie is None:
        return
    CLI_SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    CLI_SESSION_PATH.write_text(
        json.dumps(
            {
                "api_url": api_url,
                "cookie_name": cookie[0],
                "cookie_value": cookie[1],
                "email": payload.get("email", ""),
                "workspace_name": payload.get("name", ""),
                "saved_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _http_json(
    method: str,
    url: str,
    *,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[dict[str, Any], Any]:
    request_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if headers:
        request_headers.update(headers)
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = urllib_request.Request(url, data=body, headers=request_headers, method=method.upper())
    try:
        with urllib_request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            return payload, response.headers
    except urllib_error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {}
        detail = payload.get("detail") or payload.get("error") or raw or str(exc.reason)
        raise SystemExit(f"{exc.code}: {detail}") from exc
    except urllib_error.URLError as exc:
        raise SystemExit(f"Nova API unreachable at {url}: {exc.reason}") from exc


async def _run_auth_command(args: argparse.Namespace) -> None:
    api_url = _resolve_api_url(getattr(args, "api_url", None))

    if args.auth_command == "status":
        setup_status, _ = _http_json("GET", f"{api_url}/setup/status")
        session_headers = _cli_session_headers(api_url)
        session_payload: dict[str, Any] = {"authenticated": False}
        if session_headers:
            try:
                session_payload, _ = _http_json("GET", f"{api_url}/auth/session", headers=session_headers)
            except SystemExit:
                session_payload = {"authenticated": False}
        print(
            json.dumps(
                {
                    "api_url": api_url,
                    "session_saved": bool(session_headers),
                    "authenticated": bool(session_payload.get("authenticated")),
                    "workspace": session_payload.get("workspace"),
                    "setup": setup_status,
                },
                indent=2,
            )
        )
        return

    if args.auth_command == "signup":
        setup_status, _ = _http_json("GET", f"{api_url}/setup/status")
        if setup_status.get("needs_setup") and args.bootstrap_token:
            payload, headers = _http_json(
                "POST",
                f"{api_url}/setup/bootstrap",
                data={
                    "name": (args.workspace_name or args.company or args.name).strip(),
                    "owner_name": args.name.strip(),
                    "email": args.email,
                    "password": args.password,
                    "plan": args.plan,
                    "api_key": args.workspace_api_key,
                    "bootstrap_token": args.bootstrap_token,
                },
            )
        else:
            payload, headers = _http_json(
                "POST",
                f"{api_url}/auth/signup",
                data={
                    "name": args.name,
                    "email": args.email,
                    "password": args.password,
                    "company": args.company,
                    "plan": args.plan,
                    "api_key": args.workspace_api_key,
                },
            )
        _persist_cli_session(api_url, headers, payload)
        print(json.dumps({"status": "signed_up", "api_url": api_url, **payload}, indent=2))
        return

    if args.auth_command == "login":
        payload, headers = _http_json(
            "POST",
            f"{api_url}/auth/login",
            data={"email": args.email, "password": args.password},
        )
        _persist_cli_session(api_url, headers, payload)
        print(json.dumps({"status": "logged_in", "api_url": api_url, **payload}, indent=2))
        return

    if args.auth_command == "whoami":
        headers = _cli_session_headers(api_url)
        if args.api_key:
            payload, _ = _http_json("GET", f"{api_url}/workspaces/me", headers={"x-api-key": args.api_key})
        else:
            payload, _ = _http_json("GET", f"{api_url}/auth/me", headers=headers)
        print(json.dumps(payload, indent=2))
        return

    if args.auth_command == "profile":
        payload_data: dict[str, Any] = {}
        if args.owner_name is not None:
            payload_data["owner_name"] = args.owner_name
        if args.preferred_name is not None:
            payload_data["preferred_name"] = args.preferred_name
        if args.role_title is not None:
            payload_data["role_title"] = args.role_title
        if args.birth_date is not None:
            payload_data["birth_date"] = args.birth_date
        if args.default_assistant is not None:
            payload_data["default_assistant"] = args.default_assistant
        if args.complete_onboarding:
            payload_data["complete_onboarding"] = True
        if args.reopen_onboarding:
            payload_data["reopen_onboarding"] = True
        if not payload_data:
            raise SystemExit("auth profile requires at least one field to update")
        headers = {"x-api-key": args.api_key} if args.api_key else _cli_session_headers(api_url)
        payload, _ = _http_json(
            "PATCH",
            f"{api_url}/workspaces/me/profile",
            data=payload_data,
            headers=headers,
        )
        print(json.dumps(payload, indent=2))
        return

    if args.auth_command == "logout":
        session_headers = _cli_session_headers(api_url)
        if session_headers:
            try:
                _http_json("POST", f"{api_url}/auth/logout", data={}, headers=session_headers)
            except SystemExit:
                pass
        _clear_cli_session()
        print(json.dumps({"status": "logged_out", "api_url": api_url}, indent=2))
        return


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nova", description="Nova OS v4.0.5 control plane CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start")
    start.add_argument("--host")
    start.add_argument("--port", type=int)
    start.add_argument("--bridge-port", type=int)
    start.add_argument("--no-open-browser", action="store_true")
    subparsers.add_parser("help")
    init_cmd = subparsers.add_parser("init")
    init_cmd.add_argument("--json", action="store_true")
    serve = subparsers.add_parser("serve")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    serve.add_argument("--bridge-port", type=int)
    serve.add_argument("--api-only", action="store_true")
    serve.add_argument("--open-browser", action="store_true")
    subparsers.add_parser("status")
    subparsers.add_parser("version")
    subparsers.add_parser("seed")
    subparsers.add_parser("watch")
    skill = subparsers.add_parser("skill")
    skill_sub = skill.add_subparsers(dest="skill_command", required=True)
    skill_install = skill_sub.add_parser("install")
    skill_install.add_argument("--agent", choices=["codex", "gemini", "opencode", "all"], default="codex")
    skill_install.add_argument("--json", action="store_true")
    discover = subparsers.add_parser("discover")
    discover.add_argument("--json", action="store_true")

    connect = subparsers.add_parser("connect")
    connect.add_argument("agent_key")
    connect.add_argument("--workspace")
    connect.add_argument("--config", default="{}")
    connect.add_argument("--url")
    connect.add_argument("--user")
    connect.add_argument("--password")
    connect.add_argument("--can-do", action="append", default=[])
    connect.add_argument("--cannot-do", action="append", default=[])

    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--agent", required=True)
    evaluate.add_argument("--action", required=True)
    evaluate.add_argument("--payload", default="{}")
    evaluate.add_argument("--workspace")

    chat = subparsers.add_parser("chat")
    chat.add_argument("message")
    chat.add_argument("--agent")
    chat.add_argument("--workspace")

    validate = subparsers.add_parser("validate")
    validate.add_argument("--agent")
    validate.add_argument("--action", required=True)
    validate.add_argument("--payload", default="{}")
    validate.add_argument("--workspace")

    agents = subparsers.add_parser("agents")
    agents.add_argument("subject", nargs="?")
    agents.add_argument("action_name", nargs="?")
    agents.add_argument("prompt", nargs="?")
    agents.add_argument("--name")
    agents.add_argument("--model")
    agents.add_argument("--provider", default="openai")
    agents.add_argument("--workspace")
    agents.add_argument("--payload", default="{}")
    agents.add_argument("--approval-mode", default="suggest")

    agent_alias = subparsers.add_parser("agent")
    agent_alias.add_argument("subject", nargs="?")
    agent_alias.add_argument("action_name", nargs="?")
    agent_alias.add_argument("prompt", nargs="?")
    agent_alias.add_argument("--name")
    agent_alias.add_argument("--model")
    agent_alias.add_argument("--provider", default="openai")
    agent_alias.add_argument("--workspace")
    agent_alias.add_argument("--payload", default="{}")
    agent_alias.add_argument("--approval-mode", default="suggest")

    ledger = subparsers.add_parser("ledger")
    ledger_sub = ledger.add_subparsers(dest="ledger_command", required=True)
    ledger_verify = ledger_sub.add_parser("verify")
    ledger_verify.add_argument("--workspace")
    ledger_export = ledger_sub.add_parser("export")
    ledger_export.add_argument("--format", default="json", choices=["json"])
    ledger_export.add_argument("--output", required=True)
    ledger_export.add_argument("--workspace")

    gateway = subparsers.add_parser("gateway")
    gateway_sub = gateway.add_subparsers(dest="gateway_command", required=True)
    gateway_sub.add_parser("status")

    stream = subparsers.add_parser("stream")
    stream.add_argument("--agent", required=True)
    stream.add_argument("--limit", type=int, default=10)
    stream.add_argument("--workspace")

    shield = subparsers.add_parser("shield")
    shield.add_argument("--listen", default="0.0.0.0:9002")

    auth = subparsers.add_parser("auth")
    auth_sub = auth.add_subparsers(dest="auth_command", required=True)

    auth_status = auth_sub.add_parser("status")
    auth_status.add_argument("--api-url")

    auth_signup = auth_sub.add_parser("signup")
    auth_signup.add_argument("--name", required=True)
    auth_signup.add_argument("--email", required=True)
    auth_signup.add_argument("--password", required=True)
    auth_signup.add_argument("--company")
    auth_signup.add_argument("--plan", default="trial")
    auth_signup.add_argument("--workspace-name")
    auth_signup.add_argument("--workspace-api-key", "--api-key", dest="workspace_api_key")
    auth_signup.add_argument("--bootstrap-token")
    auth_signup.add_argument("--api-url")

    auth_login = auth_sub.add_parser("login")
    auth_login.add_argument("--email", required=True)
    auth_login.add_argument("--password", required=True)
    auth_login.add_argument("--api-url")

    auth_whoami = auth_sub.add_parser("whoami")
    auth_whoami.add_argument("--api-key")
    auth_whoami.add_argument("--api-url")

    auth_profile = auth_sub.add_parser("profile")
    auth_profile.add_argument("--owner-name")
    auth_profile.add_argument("--preferred-name")
    auth_profile.add_argument("--role-title")
    auth_profile.add_argument("--birth-date")
    auth_profile.add_argument("--default-assistant", choices=["nova", "melissa", "both"])
    auth_profile.add_argument("--complete-onboarding", action="store_true")
    auth_profile.add_argument("--reopen-onboarding", action="store_true")
    auth_profile.add_argument("--api-key")
    auth_profile.add_argument("--api-url")

    auth_logout = auth_sub.add_parser("logout")
    auth_logout.add_argument("--api-url")

    return parser


def parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    raw_args = list(argv if argv is not None else sys.argv[1:])
    if not raw_args:
        raw_args = ["start"]
    else:
        first = raw_args[0]
        if first in ("-h", "--help"):
            raw_args = ["help"]
        elif not first.startswith("-"):
            raw_args[0] = CLI_COMMAND_ALIASES.get(first.lower(), first.lower())
    return parser.parse_args(raw_args)


async def _resolve_agent_id(kernel: Any, workspace_id: str, requested_agent: str | None) -> str:
    agents = await kernel.agent_registry.list(workspace_id)
    if requested_agent:
        for agent in agents:
            if agent.id == requested_agent or agent.name == requested_agent:
                return agent.id
    if agents:
        return agents[0].id
    agent = await kernel.agent_registry.create(
        workspace_id=workspace_id,
        name="CLI Operator",
        model="openai/gpt-4o-mini",
        provider="openai",
    )
    return agent.id


def _parse_payload(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("payload must decode to a JSON object")
    return payload


def _console() -> Console | None:
    return Console() if Console is not None else None


def _print_discovery_table(agents: list[dict[str, Any]], inventory: dict[str, Any] | None = None) -> None:
    console = _console()
    if console is None or Table is None:
        print(json.dumps({"agents": agents, "inventory": inventory or {}}, indent=2))
        return
    if Panel is not None:
        console.print(
            Panel.fit(
                "[bold bright_blue]NOVA OS[/bold bright_blue]\n"
                "[white]Host discovery • governed runtime • operator visibility[/white]",
                border_style="bright_blue",
            )
        )
    table = Table(title="Nova OS - Agent Discovery Scan")
    table.add_column("#", style="cyan")
    table.add_column("Agent", style="bold")
    table.add_column("Status")
    table.add_column("Detection")
    table.add_column("Confid.")
    for index, agent in enumerate(agents, start=1):
        status = "online" if agent.get("is_running") else "idle"
        detection = "+".join(agent.get("detection_methods") or [agent.get("detection_method") or "?"])
        table.add_row(str(index), agent.get("name", "Unknown"), status, detection, f"{round((agent.get('confidence') or 0) * 100)}%")
    console.print(table)
    if inventory:
        summary = inventory.get("summary", {})
        host = inventory.get("host", {})
        signals = inventory.get("signals", {})
        console.print(
            f"[bold blue]Host inventory[/bold blue] "
            f"repos={summary.get('repositories', 0)} "
            f"terminals={summary.get('terminals', 0)} "
            f"active={summary.get('active_repositories', 0)} "
            f"codex_home={'yes' if signals.get('has_codex_home') else 'no'} "
            f"platform={host.get('platform') or signals.get('platform') or 'unknown'} "
            f"pkgmgr={((host.get('package_manager') or {}).get('name')) or 'n/a'}"
        )
        tooling = [item for item in inventory.get("tooling", []) if item.get("installed")]
        if tooling:
            tool_table = Table(title="Installed toolchains")
            tool_table.add_column("Tool", style="bold")
            tool_table.add_column("Category")
            tool_table.add_column("Version")
            for item in tooling[:12]:
                tool_table.add_row(item.get("label", item.get("key", "?")), item.get("category", "?"), item.get("version") or "detected")
            console.print(tool_table)

        recommendations = inventory.get("recommended_installs", [])
        if recommendations:
            install_table = Table(title="Recommended installs")
            install_table.add_column("Tool", style="bold yellow")
            install_table.add_column("Reason")
            install_table.add_column("Install")
            for item in recommendations[:8]:
                install_table.add_row(item.get("tool", "?"), item.get("reason", ""), item.get("install_command") or "manual")
            console.print(install_table)


async def _agent_metrics(kernel: Any, agent_id: str) -> dict[str, Any]:
    from nova.storage.database import session_scope
    from nova.storage.repositories.evaluation_repo import EvaluationRepository

    async with session_scope() as session:
        repo = EvaluationRepository(session)
        rows = await repo.list_by_agent(agent_id, limit=200)
    return {
        "total_actions": len(rows),
        "blocked": len([row for row in rows if row.decision == "BLOCK"]),
        "escalated": len([row for row in rows if row.decision == "ESCALATE"]),
        "avg_risk_score": round(sum(row.risk_score for row in rows) / max(len(rows), 1), 2) if rows else 0,
        "last_action": rows[0].created_at.isoformat() if rows else None,
    }


async def _serve_shield(kernel: Any, listen: str) -> None:
    import uvicorn

    host, _, port_text = listen.partition(":")
    port = int(port_text or "9002")
    from nova.api.server import create_app

    app = create_app(kernel)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "nova-shield", "version": _nova_version()}

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=host or "0.0.0.0",
            port=port,
            log_level=kernel.config.log_level.lower(),
        )
    )
    await server.serve()


async def _serve_api(
    kernel: Any,
    *,
    host: str | None = None,
    port: int | None = None,
    api_only: bool = False,
    open_browser: bool = False,
) -> None:
    import uvicorn

    from nova.api.server import create_app
    from nova.bridge.bridge_server import NovaBridge
    from nova.utils.browser import open_dashboard_when_ready

    await kernel.initialize()
    kernel.start_discovery_background()
    if not api_only:
        kernel._bridge = NovaBridge(kernel, kernel.config)
        try:
            await kernel._bridge.start()
        except OSError as exc:
            if not await kernel._handle_address_in_use(exc, open_browser=open_browser):
                raise RuntimeError(kernel._port_conflict_message("bridge", kernel.config.bridge_port)) from exc
            return
    app = create_app(kernel, serve_frontend=not api_only)
    if open_browser and not api_only:
        kernel._background_tasks.append(
            asyncio.create_task(
                open_dashboard_when_ready(kernel.config),
                name="nova-open-dashboard",
            )
        )
    kernel._api_server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=host or kernel.config.host,
            port=port or kernel.config.api_port,
            log_level=kernel.config.log_level.lower(),
        )
    )
    try:
        await kernel._api_server.serve()
    except OSError as exc:
        if not await kernel._handle_address_in_use(exc, open_browser=open_browser):
            raise RuntimeError(kernel._port_conflict_message("api", kernel.config.api_port)) from exc
    finally:
        await kernel.shutdown()


async def run_async(args: argparse.Namespace, raw_args: list[str] | None = None) -> None:
    if args.command == "help":
        from nova.utils.formatting import command_launchpad

        print(command_launchpad())
        return

    if args.command == "auth":
        await _run_auth_command(args)
        return

    if args.command == "version":
        print(f"Nova OS v{_nova_version()} (Enterprise) - Python {platform.python_version()}")
        return

    if args.command == "skill":
        from nova.agent_skills import install_skill

        payload = install_skill(args.agent)
        print(json.dumps(payload, indent=2))
        return

    try:
        from nova.config import NovaConfig
        from nova.kernel import get_kernel
        from nova.utils.browser import local_dashboard_url
        from nova.utils.formatting import launch_banner
    except ModuleNotFoundError as exc:
        _attempt_bootstrap_reexec(list(raw_args or []), exc)

    config = NovaConfig()
    if args.command == "start":
        print(launch_banner(dashboard_url=local_dashboard_url(config), version=config.version), flush=True)

    kernel = get_kernel(config)
    if getattr(args, "host", None):
        kernel.config.host = args.host
    if getattr(args, "port", None):
        kernel.config.api_port = args.port
    if getattr(args, "bridge_port", None):
        kernel.config.bridge_port = args.bridge_port
    await kernel.initialize()
    default_workspace = await kernel.workspace_manager.ensure_default_workspace()

    if args.command == "init":
        payload = {"status": "initialized", "workspace_id": default_workspace.id}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print("Nova initialized")
        return

    if args.command == "start":
        try:
            await kernel.start(open_browser=not getattr(args, "no_open_browser", False))
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
        return

    if args.command == "serve":
        try:
            await _serve_api(
                kernel,
                host=getattr(args, "host", None),
                port=getattr(args, "port", None),
                api_only=getattr(args, "api_only", False),
                open_browser=getattr(args, "open_browser", False),
            )
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
        return

    if args.command == "status":
        print(json.dumps(_to_payload(await kernel.get_status()), indent=2))
        return

    if args.command == "watch":
        queue = kernel.events.subscribe()
        console = _console()
        try:
            agents = [_to_payload(agent) for agent in await kernel.discovery.scan(force=True)]
            if console is not None:
                console.print(f"[bold]Watching Nova runtime[/bold] - {len(agents)} agents discovered")
            else:
                print(json.dumps({"watching": True, "discovered_agents": len(agents)}, indent=2))
            while True:
                event = await queue.get()
                payload = {"type": event.type, "timestamp": event.timestamp.isoformat(), **event.payload}
                if console is not None:
                    console.print(f"[cyan]{event.timestamp.isoformat()}[/cyan] {event.type} {json.dumps(event.payload, default=str)}")
                else:
                    print(json.dumps(payload, default=str))
        finally:
            kernel.events.unsubscribe(queue)
        return

    if args.command == "discover":
        agents = [_to_payload(agent) for agent in await kernel.discovery.scan(force=True)]
        payload = {"agents": agents, "inventory": kernel.discovery.last_inventory}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            _print_discovery_table(agents, kernel.discovery.last_inventory)
        return

    if args.command == "connect":
        config = _parse_payload(args.config)
        if args.url:
            config["n8n_url"] = args.url
            config["base_url"] = args.url
        if args.user:
            config["user"] = args.user
        if args.password:
            config["password"] = args.password
        result = await kernel.discovery.connect(
            agent_key=args.agent_key,
            workspace_id=args.workspace or default_workspace.id,
            config=config,
            permissions={
                key: value
                for key, value in {
                    "can_do": list(args.can_do or []),
                    "cannot_do": list(args.cannot_do or []),
                }.items()
                if value
            },
        )
        print(json.dumps(_to_payload(result), indent=2))
        return

    if args.command == "chat":
        from nova.nova_types import EvaluationRequest

        workspace_id = args.workspace or default_workspace.id
        agent_id = await _resolve_agent_id(kernel, workspace_id, args.agent)
        result = await kernel.evaluate(
            EvaluationRequest(
                agent_id=agent_id,
                workspace_id=workspace_id,
                action="chat",
                payload={"message": args.message},
                source="cli_chat",
            )
        )
        print(json.dumps(_to_payload(result), indent=2))
        return

    if args.command in {"evaluate", "validate"}:
        from nova.nova_types import EvaluationRequest

        workspace_id = args.workspace or default_workspace.id
        agent_id = await _resolve_agent_id(kernel, workspace_id, getattr(args, "agent", None))
        result = await kernel.evaluate(
            EvaluationRequest(
                agent_id=agent_id,
                workspace_id=workspace_id,
                action=args.action,
                payload=_parse_payload(args.payload),
                source="cli",
            )
        )
        print(json.dumps(_to_payload(result), indent=2))
        return

    if args.command in {"agents", "agent"}:
        from nova.discovery.agent_manifest import AgentTask

        subject = args.subject
        if subject in {None, "list"}:
            registered = [_to_payload(agent) for agent in await kernel.agent_registry.list(default_workspace.id)]
            discovered = [_to_payload(agent) for agent in await kernel.discovery.scan(force=False)]
            print(json.dumps({"registered": registered, "discovered": discovered}, indent=2))
            return
        if subject == "create":
            if not args.name or not args.model:
                raise SystemExit("agents create requires --name and --model")
            agent = await kernel.agent_registry.create(
                workspace_id=args.workspace or default_workspace.id,
                name=args.name,
                model=args.model,
                provider=args.provider,
            )
            print(json.dumps(_to_payload(agent), indent=2))
            return
        if args.action_name == "status":
            agent_record = await kernel.agent_registry.get(subject)
            if agent_record is None:
                discovered = await kernel.discovery.get_agent(subject)
                if discovered is None:
                    raise SystemExit(f"agent {subject} not found")
                print(json.dumps(_to_payload(await kernel.discovery.get_status(subject)), indent=2))
                return
            payload = _to_payload(agent_record)
            payload["metrics"] = _to_payload(await _agent_metrics(kernel, subject))
            print(json.dumps(payload, indent=2))
            return
        if args.action_name == "send":
            discovery_key = subject
            agent_record = await kernel.agent_registry.get(subject)
            if agent_record is not None:
                discovery_key = str((agent_record.metadata or {}).get("discovery", {}).get("agent_key") or subject)
            result = await kernel.discovery.send_task(
                agent_key=discovery_key,
                workspace_id=args.workspace or default_workspace.id,
                task=AgentTask(
                    prompt=args.prompt or "",
                    model=args.model,
                    payload=_parse_payload(args.payload),
                    approval_mode=args.approval_mode,
                ),
            )
            print(json.dumps(_to_payload(result), indent=2))
            return
        raise SystemExit("Unsupported agents command")

    if args.command == "ledger":
        if args.ledger_command == "verify":
            if args.workspace:
                workspace_ids = [args.workspace]
            else:
                workspace_ids = [workspace.id for workspace in await kernel.workspace_manager.list_workspaces()]
            results = []
            for workspace_id in workspace_ids:
                result = await kernel.ledger.hash_chain.verify_integrity(workspace_id)
                results.append({"workspace_id": workspace_id, **_to_payload(result)})
            print(json.dumps(results if len(results) > 1 else results[0], indent=2))
            return
        if args.ledger_command == "export":
            workspace_id = args.workspace or default_workspace.id
            entries = await kernel.ledger.list_entries(workspace_id, limit=10_000)
            output = Path(args.output)
            output.write_text(json.dumps([{"action_id": item.action_id, "eval_id": item.eval_id, "hash": item.hash} for item in entries], indent=2), encoding="utf-8")
            print(str(output))
            return

    if args.command == "gateway" and args.gateway_command == "status":
        print(json.dumps(kernel.gateway.status(), indent=2))
        return

    if args.command == "stream":
        from nova.storage.database import session_scope
        from nova.storage.repositories.evaluation_repo import EvaluationRepository

        workspace_id = args.workspace or default_workspace.id
        agent_id = await _resolve_agent_id(kernel, workspace_id, args.agent)
        async with session_scope() as session:
            repo = EvaluationRepository(session)
            rows = await repo.list_by_agent(agent_id, limit=args.limit)
        print(
            json.dumps(
                [
                    {
                        "id": row.id,
                        "action": row.action,
                        "decision": row.decision,
                        "risk_score": row.risk_score,
                        "status": row.status,
                        "provider": row.provider,
                        "created_at": row.created_at.isoformat(),
                    }
                    for row in rows
                ],
                indent=2,
            )
        )
        return

    if args.command == "shield":
        await _serve_shield(kernel, args.listen)
        return

    if args.command == "seed":
        from scripts.seed_data import seed

        await seed(kernel)
        print("seed complete")


def main(argv: list[str] | None = None) -> None:
    raw_args = list(argv if argv is not None else sys.argv[1:])
    legacy_args = _legacy_dispatch_argv(raw_args)
    if legacy_args is not None:
        _run_legacy_cli(legacy_args)
        return
    args = parse_cli_args(raw_args)
    asyncio.run(run_async(args, raw_args=raw_args))


if __name__ == "__main__":
    main()
