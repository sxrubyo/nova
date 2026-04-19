from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_kernel_imports_without_resource_module() -> None:
    script = """
import builtins
orig_import = builtins.__import__

def fake_import(name, *args, **kwargs):
    if name == "resource":
        raise ModuleNotFoundError("No module named 'resource'")
    return orig_import(name, *args, **kwargs)

builtins.__import__ = fake_import
import nova.kernel
print("kernel-import-ok")
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "kernel-import-ok" in result.stdout
