"""Tests for install/distribution entrypoints."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_install_script_delegates_python_setup_to_bootstrap_module() -> None:
    install_script = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")

    assert "nova/bootstrap.py" in install_script
    assert "python3 -m pip install -r" not in install_script


def test_npm_package_exposes_nova_bin() -> None:
    package_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))

    assert package_json["name"] == "nova-os"
    assert package_json["bin"]["nova"] == "bin/nova.js"
    assert "bin/nova.js" in package_json["files"]
    assert "nova/**/*.py" in package_json["files"]
    assert "nova.py" in package_json["files"]


def test_npmignore_excludes_python_cache_artifacts() -> None:
    npmignore = (REPO_ROOT / ".npmignore").read_text(encoding="utf-8")

    assert "__pycache__/" in npmignore
    assert "*.pyc" in npmignore
