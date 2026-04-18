"""Nova OS CLI entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
from pathlib import Path
from typing import Any

import uvicorn

from fastapi import FastAPI
from nova.api.dependencies import to_payload
from nova.config import NovaConfig
from nova.constants import NOVA_VERSION
from nova.kernel import get_kernel
from nova.storage.database import session_scope
from nova.storage.repositories.evaluation_repo import EvaluationRepository
from nova.types import EvaluationRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nova", description="Nova OS v4.0.0 control plane CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("start")
    subparsers.add_parser("status")
    subparsers.add_parser("version")
    subparsers.add_parser("seed")
    subparsers.add_parser("watch")

    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--agent", required=True)
    evaluate.add_argument("--action", required=True)
    evaluate.add_argument("--payload", default="{}")
    evaluate.add_argument("--workspace")

    validate = subparsers.add_parser("validate")
    validate.add_argument("--agent")
    validate.add_argument("--action", required=True)
    validate.add_argument("--payload", default="{}")
    validate.add_argument("--workspace")

    agents = subparsers.add_parser("agents")
    agents_sub = agents.add_subparsers(dest="agents_command", required=True)
    agents_sub.add_parser("list")
    agents_create = agents_sub.add_parser("create")
    agents_create.add_argument("--name", required=True)
    agents_create.add_argument("--model", required=True)
    agents_create.add_argument("--provider", default="openai")
    agents_create.add_argument("--workspace")

    agent_alias = subparsers.add_parser("agent")
    agent_alias_sub = agent_alias.add_subparsers(dest="agents_command", required=True)
    agent_alias_sub.add_parser("list")
    agent_alias_create = agent_alias_sub.add_parser("create")
    agent_alias_create.add_argument("--name", required=True)
    agent_alias_create.add_argument("--model", required=True)
    agent_alias_create.add_argument("--provider", default="openai")
    agent_alias_create.add_argument("--workspace")

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

    return parser


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


async def _serve_shield(kernel: Any, listen: str) -> None:
    host, _, port_text = listen.partition(":")
    port = int(port_text or "9002")
    from nova.api.server import create_app

    app = create_app(kernel)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "nova-shield", "version": NOVA_VERSION}

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=host or "0.0.0.0",
            port=port,
            log_level=kernel.config.log_level.lower(),
        )
    )
    await server.serve()


async def run_async(args: argparse.Namespace) -> None:
    kernel = get_kernel(NovaConfig())
    await kernel.initialize()
    default_workspace = await kernel.workspace_manager.ensure_default_workspace()

    if args.command == "start":
        await kernel.start()
        return

    if args.command == "status":
        print(json.dumps(to_payload(await kernel.get_status()), indent=2))
        return

    if args.command == "watch":
        print(json.dumps(to_payload(await kernel.get_status()), indent=2))
        return

    if args.command == "version":
        print(f"Nova OS v{NOVA_VERSION} (Enterprise) - Python {platform.python_version()}")
        return

    if args.command in {"evaluate", "validate"}:
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
        print(json.dumps(to_payload(result), indent=2))
        return

    if args.command in {"agents", "agent"}:
        if args.agents_command == "list":
            agents = await kernel.agent_registry.list(default_workspace.id)
            print(json.dumps([to_payload(agent) for agent in agents], indent=2))
            return
        if args.agents_command == "create":
            agent = await kernel.agent_registry.create(
                workspace_id=args.workspace or default_workspace.id,
                name=args.name,
                model=args.model,
                provider=args.provider,
            )
            print(json.dumps(to_payload(agent), indent=2))
            return

    if args.command == "ledger":
        if args.ledger_command == "verify":
            if args.workspace:
                workspace_ids = [args.workspace]
            else:
                workspace_ids = [workspace.id for workspace in await kernel.workspace_manager.list_workspaces()]
            results = []
            for workspace_id in workspace_ids:
                result = await kernel.ledger.hash_chain.verify_integrity(workspace_id)
                results.append({"workspace_id": workspace_id, **to_payload(result)})
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


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(run_async(args))


if __name__ == "__main__":
    main()
