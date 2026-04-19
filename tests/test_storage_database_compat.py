"""Regression tests for database engine selection."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


def test_init_engine_respects_explicit_postgres_url(monkeypatch, tmp_path: Path) -> None:
    import nova.storage.database as storage_database
    from nova.config import NovaConfig

    captured: dict[str, str] = {}

    def fake_create_async_engine(url: str, **_: object):
        captured["url"] = url
        return SimpleNamespace(sync_engine=object())

    monkeypatch.setattr(storage_database, "_engine", None)
    monkeypatch.setattr(storage_database, "_session_factory", None)
    monkeypatch.setattr(storage_database, "create_async_engine", fake_create_async_engine)
    monkeypatch.setattr(storage_database, "async_sessionmaker", lambda *args, **kwargs: ("factory", args, kwargs))
    monkeypatch.setattr(storage_database, "event", SimpleNamespace(listen=lambda *args, **kwargs: None))
    monkeypatch.setattr(storage_database.PLATFORM, "db_engine", "sqlite")

    config = NovaConfig(
        NOVA_DB_URL="postgresql+asyncpg://user:pass@db:5432/nova",
        NOVA_WORKSPACE_ROOT=tmp_path,
        NOVA_DATA_DIR=tmp_path / "data",
    )

    storage_database.init_engine(config)

    assert captured["url"] == "postgresql+asyncpg://user:pass@db:5432/nova"
    assert config.db_url == "postgresql+asyncpg://user:pass@db:5432/nova"
