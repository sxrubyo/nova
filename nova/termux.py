"""Termux/Android helpers used only on mobile environments."""

from __future__ import annotations

import os
import shutil
import subprocess

from nova.platform import PLATFORM


def vibrate(ms: int = 100) -> None:
    """Trigger device haptic feedback when Termux:API is installed."""

    if shutil.which("termux-vibrate"):
        subprocess.run(["termux-vibrate", "-d", str(ms)], capture_output=True, text=True, check=False)


def notify(title: str, msg: str) -> None:
    """Send a local Android notification when available."""

    if shutil.which("termux-notification"):
        subprocess.run(
            ["termux-notification", "--title", title, "--content", msg],
            capture_output=True,
            text=True,
            check=False,
        )


def battery_status() -> dict:
    """Return Android battery info when Termux:API is installed."""

    if shutil.which("termux-battery-status"):
        import json

        result = subprocess.run(
            ["termux-battery-status"],
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            return json.loads(result.stdout)
        except Exception:  # noqa: BLE001
            return {}
    return {}


def wake_lock(acquire: bool = True) -> None:
    """Prevent Android from suspending Nova during long tasks."""

    command = "termux-wake-lock" if acquire else "termux-wake-unlock"
    if shutil.which(command):
        subprocess.run([command], capture_output=True, text=True, check=False)


def get_storage_path() -> str:
    """Return the preferred shared storage path on Android."""

    shared = os.path.expanduser("~/storage/shared")
    if os.path.exists(shared):
        return shared
    return PLATFORM.nova_dir
