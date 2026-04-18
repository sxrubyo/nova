"""Zero-dependency platform detection for Nova OS."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from typing import Literal

PlatformType = Literal["termux", "linux", "macos", "windows", "unknown"]
DatabaseEngine = Literal["postgres", "sqlite"]
ProcessManager = Literal["systemd", "pm2", "screen", "nohup"]


@dataclass(slots=True)
class PlatformInfo:
    type: PlatformType
    has_docker: bool
    has_systemd: bool
    has_postgres: bool
    has_node: bool
    home: str
    nova_dir: str
    db_engine: DatabaseEngine
    process_manager: ProcessManager
    python: str


def detect() -> PlatformInfo:
    """Detect the current host runtime with no external dependencies."""

    home = os.path.expanduser("~")
    prefix = os.environ.get("PREFIX", "")
    is_termux = (
        "com.termux" in prefix
        or os.path.exists("/data/data/com.termux")
        or os.environ.get("TERMUX_VERSION") is not None
    )

    if is_termux:
        platform_type: PlatformType = "termux"
    elif sys.platform == "win32":
        platform_type = "windows"
    elif sys.platform == "darwin":
        platform_type = "macos"
    elif sys.platform.startswith("linux"):
        platform_type = "linux"
    else:
        platform_type = "unknown"

    has_docker = shutil.which("docker") is not None and not is_termux
    has_systemd = shutil.which("systemctl") is not None and not is_termux
    has_postgres = shutil.which("pg_isready") is not None and not is_termux
    has_node = shutil.which("node") is not None

    if has_systemd:
        process_manager: ProcessManager = "systemd"
    elif shutil.which("pm2") is not None:
        process_manager = "pm2"
    elif shutil.which("screen") is not None:
        process_manager = "screen"
    else:
        process_manager = "nohup"

    nova_dir = os.path.join(home, ".nova")

    return PlatformInfo(
        type=platform_type,
        has_docker=has_docker,
        has_systemd=has_systemd,
        has_postgres=has_postgres,
        has_node=has_node,
        home=home,
        nova_dir=nova_dir,
        db_engine="postgres" if has_postgres else "sqlite",
        process_manager=process_manager,
        python=sys.executable,
    )


PLATFORM = detect()
