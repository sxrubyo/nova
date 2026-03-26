"""Async database configuration and session management."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from nova.config import NovaConfig
from nova.storage.models import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _sqlite_pragma(dbapi_connection: Any, _: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_engine(config: NovaConfig) -> AsyncEngine:
    """Initialize the shared async engine and session factory."""

    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(config.db_url, echo=False, future=True)
        if config.db_url.startswith("sqlite"):
            event.listen(_engine.sync_engine, "connect", _sqlite_pragma)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


async def init_database(config: NovaConfig) -> None:
    """Create all tables if they do not already exist."""

    engine = init_engine(config)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the shared async session factory."""

    if _session_factory is None:
        raise RuntimeError("database engine is not initialized")
    return _session_factory


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Yield an async session with commit-or-rollback semantics."""

    session = get_session_factory()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def dispose_engine() -> None:
    """Dispose the shared engine."""

    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
