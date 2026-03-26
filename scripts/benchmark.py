"""Micro-benchmark for the evaluation pipeline."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nova.kernel import get_kernel
from nova.types import EvaluationRequest


async def main() -> None:
    kernel = get_kernel()
    await kernel.initialize()
    workspace = await kernel.workspace_manager.ensure_default_workspace()
    agents = await kernel.agent_registry.list(workspace.id)
    if not agents:
        agent = await kernel.agent_registry.create(workspace.id, "benchmark-agent", "gpt-4o-mini", "openai")
    else:
        agent = agents[0]
    started = time.monotonic()
    for _ in range(100):
        await kernel.evaluate(EvaluationRequest(agent_id=agent.id, workspace_id=workspace.id, action="generate_response", payload={"prompt": "hello"}, source="benchmark"))
    duration = time.monotonic() - started
    print(json.dumps({"evaluations": 100, "duration_seconds": round(duration, 2), "per_eval_ms": round(duration * 1000 / 100, 2)}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
