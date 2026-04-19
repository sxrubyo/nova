"""Compatibility tests for legacy env names."""

from __future__ import annotations

from nova.config import NovaConfig


def test_database_url_legacy_env_is_accepted(monkeypatch) -> None:
    monkeypatch.delenv("NOVA_DB_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@db:5432/nova")

    config = NovaConfig()

    assert config.db_url == "postgresql+asyncpg://user:pass@db:5432/nova"


def test_secret_key_legacy_env_is_accepted(monkeypatch) -> None:
    monkeypatch.delenv("NOVA_JWT_SECRET", raising=False)
    monkeypatch.setenv("SECRET_KEY", "legacy-secret")

    config = NovaConfig()

    assert config.jwt_secret == "legacy-secret"
