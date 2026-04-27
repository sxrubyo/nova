from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_frontend_defaults_to_modern_runtime_port() -> None:
    content = (ROOT / "frontend" / "src" / "config" / "appConfig.js").read_text(encoding="utf-8")

    assert "const DEFAULT_API_PORT = import.meta.env.VITE_API_PORT || '9800'" in content


def test_frontend_signup_payload_matches_modern_auth_schema() -> None:
    content = (ROOT / "frontend" / "src" / "pages" / "Login.jsx").read_text(encoding="utf-8")

    assert "workspace_name: formData.company || formData.name" in content
    assert "owner_name: formData.name" in content
    assert "api.post('/auth/signup'" in content
