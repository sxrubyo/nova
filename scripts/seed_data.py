"""Seed realistic Nova OS demo data."""

from __future__ import annotations

import asyncio
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nova.kernel import NovaKernel, get_kernel
from nova.types import EvaluationRequest

WORKSPACES = [
    ("production", "Production Workspace"),
    ("staging", "Staging Workspace"),
    ("research", "Research Workspace"),
]

AGENTS = [
    ("agent-alpha", "gpt-4o", "openai", "production"),
    ("agent-beta", "claude-3.5-sonnet", "anthropic", "production"),
    ("agent-gamma", "gemini-1.5-pro", "gemini", "staging"),
    ("agent-delta", "llama-3.1-70b", "groq", "staging"),
    ("agent-epsilon", "gpt-4o-mini", "openai", "research"),
    ("agent-zeta", "mistral-large", "mistral", "research"),
    ("agent-eta", "deepseek-chat", "deepseek", "production"),
    ("agent-theta", "command-r-plus", "cohere", "staging"),
    ("agent-iota", "grok-2", "xai", "research"),
    ("agent-kappa", "openai/gpt-4o-mini", "openrouter", "production"),
    ("agent-lambda", "claude-3-haiku", "anthropic", "staging"),
    ("agent-mu", "gemini-2.0", "gemini", "research"),
]

ACTIONS = [
    "query_database",
    "send_email",
    "generate_report",
    "call_external_api",
    "modify_config",
    "access_user_data",
    "deploy_update",
]


async def seed(kernel: NovaKernel | None = None) -> None:
    kernel = kernel or get_kernel()
    await kernel.initialize()
    created_workspaces: dict[str, str] = {}
    for slug, name in WORKSPACES:
        existing = await kernel.workspace_manager.get_by_email(f"{slug}@nova.local")
        if existing is None:
            workspace = await kernel.workspace_manager.create_workspace(
                name=name,
                owner_email=f"{slug}@nova.local",
                owner_name=f"{slug.title()} Admin",
                password="nova-admin",
            )
        else:
            workspace = existing
        created_workspaces[slug] = workspace.id

    created_agents: list[str] = []
    for agent_name, model, provider, workspace_slug in AGENTS:
        workspace_id = created_workspaces[workspace_slug]
        existing_agents = await kernel.agent_registry.list(workspace_id)
        agent = next((item for item in existing_agents if item.name == agent_name), None)
        if agent is None:
            agent = await kernel.agent_registry.create(
                workspace_id=workspace_id,
                name=agent_name,
                model=model,
                provider=provider,
                capabilities=["generate_response", "query_database", "call_external_api"],
            )
        created_agents.append(agent.id)

    for _ in range(500):
        agent_id = random.choice(created_agents)
        action = random.choice(ACTIONS)
        payload = _payload_for_action(action)
        await kernel.evaluate(EvaluationRequest(agent_id=agent_id, workspace_id=None, action=action, payload=payload, source="seed"))


def _payload_for_action(action: str) -> dict:
    if action == "query_database":
        return {"query": "SELECT 1 AS value", "database_url": "sqlite+aiosqlite:///./nova.db"}
    if action == "send_email":
        return {"to": "ops@example.com", "subject": "Routine update", "body": "Hello from Nova"}
    if action == "call_external_api":
        return {"url": "https://example.com", "method": "GET", "simulate": True}
    if action == "modify_config":
        return {"path": "./data/seed-config.txt", "content": "seeded=true\n"}
    if action == "access_user_data":
        return {"user_id": "usr_123", "scope": "profile"}
    if action == "deploy_update":
        return {"version": f"2026.{random.randint(1,12)}.{random.randint(1,28)}"}
    return {"input": f"{action} request", "risk_hint": random.randint(1, 100)}


if __name__ == "__main__":
    asyncio.run(seed())
