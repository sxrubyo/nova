"""Regression coverage for the legacy interactive selector renderer."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_legacy_module():
    module_path = Path(__file__).resolve().parents[1] / "legacy" / "nova_cli_legacy.py"
    spec = importlib.util.spec_from_file_location("nova_cli_legacy_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_selector_render_line_count_ignores_ansi_sequences() -> None:
    legacy = _load_legacy_module()
    rendered = "  \033[38;5;15mNova\033[0m\n  menu\n\n"

    assert legacy._selector_render_line_count(rendered) == 3
