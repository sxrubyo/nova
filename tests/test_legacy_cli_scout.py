"""Regression coverage for legacy scout pattern compilation and matching."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


def _load_legacy_module():
    module_path = Path(__file__).resolve().parents[1] / "legacy" / "nova_cli_legacy.py"
    spec = importlib.util.spec_from_file_location("nova_cli_scout_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_cmd_scout_compiles_patterns_and_reports_findings(tmp_path, capsys) -> None:
    legacy = _load_legacy_module()
    skill = tmp_path / "skill.py"
    skill.write_text(
        "import os\n"
        "from glob import glob\n"
        "os.walk('/home/ubuntu')\n"
        "glob('*.py')\n"
        "url = 'https://transfer.sh/upload'\n"
    )

    legacy.cmd_scout(SimpleNamespace(path=str(tmp_path)))
    output = capsys.readouterr().out

    assert "Potential Exfil Signals" in output
    assert "Webhook exfil" in output
    assert "File sweep" in output
    assert "skill.py" in output
