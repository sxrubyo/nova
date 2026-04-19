"""Regression tests for database engine selection."""

from __future__ import annotations

import asyncio
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


def test_init_database_uses_sync_schema_creation_for_sqlite(monkeypatch, tmp_path: Path) -> None:
    import nova.storage.database as storage_database
    from nova.config import NovaConfig

    captured: dict[str, object] = {}

    class FakeSyncEngine:
        def dispose(self) -> None:
            captured["disposed"] = True

    monkeypatch.setattr(storage_database, "init_engine", lambda config: SimpleNamespace(config=config))
    monkeypatch.setattr(storage_database, "create_engine", lambda url, **kwargs: captured.update({"sync_url": url, "kwargs": kwargs}) or FakeSyncEngine())
    monkeypatch.setattr(storage_database.Base.metadata, "create_all", lambda engine: captured.update({"create_all_engine": engine}))

    config = NovaConfig(
        NOVA_DB_URL=f"sqlite+aiosqlite:///{tmp_path / 'nova.db'}",
        NOVA_WORKSPACE_ROOT=tmp_path,
        NOVA_DATA_DIR=tmp_path / "data",
    )

    asyncio.run(storage_database.init_database(config))

    assert captured["sync_url"] == f"sqlite:///{tmp_path / 'nova.db'}"
    assert isinstance(captured["create_all_engine"], FakeSyncEngine)
    assert captured["disposed"] is True
