"""Tests for install/distribution entrypoints."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_install_script_delegates_python_setup_to_bootstrap_module() -> None:
    install_script = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")

    assert "nova/bootstrap.py" in install_script
    assert "python3 -m pip install -r" not in install_script
    assert '$HOME/.nova/repo' in install_script
    assert '$HOME/.nova/bin' in install_script
    assert 'command -v nova' in install_script
    assert 'sudo -n true' in install_script
    assert '--api-only' not in install_script
    assert 'NOVA_BOOTSTRAP_EMBEDDED=1' in install_script
    assert 'start --no-open-browser' in install_script
    assert '/api/status' in install_script
    assert '"$NOVA_CMD" commands' in install_script
    assert 'NOVA_REPO_ARCHIVE_URL' in install_script
    assert 'NOVA_API_PORT=$API_PORT' in install_script
    assert 'NOVA_BRIDGE_PORT=$BRIDGE_PORT' in install_script


def test_windows_installer_uses_bootstrap_runtime() -> None:
    install_script = (REPO_ROOT / "install.ps1").read_text(encoding="utf-8")

    assert "nova/bootstrap.py" in install_script
    assert "raw.githubusercontent.com/sxrubyo/nova-os/main/nova.py" not in install_script
    assert "Expand-Archive" in install_script
    assert '"install"' in install_script or "'install'" in install_script
    assert '$env:NOVA_BOOTSTRAP_EMBEDDED = "1"' in install_script
    assert '.nova\\repo' in install_script
    assert '.nova\\bin' in install_script
    assert 'Get-Command nova' in install_script
    assert '& $WrapperCmd commands' in install_script
    assert '$env:NOVA_REPO_ZIP_URL' in install_script
    assert 'NOVA_API_PORT=$ApiPort' in install_script
    assert 'NOVA_BRIDGE_PORT=$BridgePort' in install_script


def test_npm_package_exposes_nova_bin() -> None:
    package_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))

    assert package_json["name"] == "nova-os"
    assert package_json["bin"]["nova"] == "bin/nova.js"
    assert "bin/nova.js" in package_json["files"]
    assert "legacy/**/*.py" in package_json["files"]
    assert "nova/**/*.py" in package_json["files"]
    assert "nova.py" in package_json["files"]
    assert "frontend/dist/**/*" in package_json["files"]


def test_runtime_type_module_does_not_shadow_python_stdlib() -> None:
    assert (REPO_ROOT / "nova" / "nova_types.py").exists()
    assert not (REPO_ROOT / "nova" / "types.py").exists()
    assert (REPO_ROOT / "backend" / "nova" / "nova_types.py").exists()
    assert not (REPO_ROOT / "backend" / "nova" / "types.py").exists()


def test_npmignore_excludes_python_cache_artifacts() -> None:
    npmignore = (REPO_ROOT / ".npmignore").read_text(encoding="utf-8")

    assert "__pycache__/" in npmignore
    assert "*.pyc" in npmignore


def test_npm_package_is_publish_ready() -> None:
    package_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))

    assert package_json["publishConfig"]["access"] == "public"
    assert package_json["repository"]["type"] == "git"
    assert package_json["repository"]["url"].endswith("sxrubyo/nova-os.git")
    assert package_json["homepage"].endswith("sxrubyo/nova-os#readme")
    assert package_json["bugs"]["url"].endswith("sxrubyo/nova-os/issues")


def test_npm_publish_workflow_exists() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "npm-publish.yml").read_text(encoding="utf-8")

    assert "npm publish" in workflow
    assert "NODE_AUTH_TOKEN" in workflow
    assert "release" in workflow or "workflow_dispatch" in workflow


def test_public_repo_keeps_only_seed_rule_templates() -> None:
    rule_names = sorted(path.name for path in (REPO_ROOT / "nova_rules").glob("*.yaml"))

    assert any(name.startswith("seed_") for name in rule_names)
    assert not any(name.startswith("admin_") for name in rule_names)
    assert not any(name.startswith("guard_") for name in rule_names)


def test_gitignore_excludes_generated_nova_rules() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "nova_rules/admin_*.yaml" in gitignore
    assert "nova_rules/guard_*.yaml" in gitignore
