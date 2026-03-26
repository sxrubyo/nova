"""Compatibility entrypoint for the standalone Nova Bridge."""

from __future__ import annotations

import asyncio

from nova.config import NovaConfig
from nova.kernel import get_kernel

NovaBridge = __import__("nova.bridge.bridge_server", fromlist=["NovaBridge"]).NovaBridge


async def _main() -> None:
    kernel = get_kernel(NovaConfig())
    await kernel.initialize()
    bridge = NovaBridge(kernel, kernel.config)
    await bridge.start()
    try:
        await asyncio.Future()
    finally:
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(_main())
