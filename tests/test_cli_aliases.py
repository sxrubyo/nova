from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_help_command_prints_usage() -> None:
    result = subprocess.run(
        [sys.executable, "nova.py", "help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "usage: nova" in result.stdout


def test_start_subcommand_is_registered() -> None:
    result = subprocess.run(
        [sys.executable, "nova.py", "start", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "usage: nova start" in result.stdout
