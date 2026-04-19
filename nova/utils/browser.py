"""Helpers to open the local Nova dashboard when the host supports it."""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import subprocess
import sys
import webbrowser

import httpx

from nova.config import NovaConfig
from nova.platform import PLATFORM


def local_dashboard_url(config: NovaConfig) -> str:
    return f"http://127.0.0.1:{config.api_port}/"


def local_docs_url(config: NovaConfig) -> str:
    return f"http://127.0.0.1:{config.api_port}/api/docs"


def bind_api_url(config: NovaConfig) -> str:
    return f"http://{config.host}:{config.api_port}"


def bind_bridge_url(config: NovaConfig) -> str:
    return f"ws://{config.host}:{config.bridge_port}"


def should_auto_open_browser() -> bool:
    if str(os.getenv("NOVA_NO_BROWSER", "")).lower() in {"1", "true", "yes", "on"}:
        return False
    if PLATFORM.type == "termux":
        return shutil.which("termux-open-url") is not None
    if sys.platform == "win32":
        return True
    if sys.platform == "darwin":
        return shutil.which("open") is not None
    if os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"):
        return True
    return False


def open_url(url: str) -> bool:
    try:
        if PLATFORM.type == "termux":
            opener = shutil.which("termux-open-url")
            if opener:
                subprocess.Popen([opener, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            return False
        if sys.platform == "darwin":
            opener = shutil.which("open")
            if opener:
                subprocess.Popen([opener, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
        if sys.platform.startswith("linux") and (os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY")):
            opener = shutil.which("xdg-open")
            if opener:
                subprocess.Popen([opener, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
        return bool(webbrowser.open(url))
    except Exception:
        return False


async def open_dashboard_when_ready(config: NovaConfig, *, timeout_seconds: float = 20.0) -> bool:
    """Wait until the local dashboard responds, then try to open it."""

    if not should_auto_open_browser():
        return False

    url = local_dashboard_url(config)
    attempts = max(1, int(timeout_seconds / 0.5))
    async with httpx.AsyncClient(timeout=1.5, follow_redirects=True) as client:
        for _ in range(attempts):
            try:
                response = await client.get(url)
                if response.status_code < 500:
                    return open_url(url)
            except Exception:
                pass
            await asyncio.sleep(0.5)
    with contextlib.suppress(Exception):
        return open_url(url)
    return False
