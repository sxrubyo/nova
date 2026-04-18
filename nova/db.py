"""Portable database bootstrap helpers for Nova OS."""

from __future__ import annotations

import asyncio
import os
import re
import sqlite3
from contextlib import asynccontextmanager
from typing import Any

from nova.platform import PLATFORM


class _SQLiteConn:
    """Async-compatible wrapper around sqlite3 for lightweight fallbacks."""

    def __init__(self, path: str):
        self._path = path
        self._conn: sqlite3.Connection | None = None

    async def __aenter__(self) -> "_SQLiteConn":
        loop = asyncio.get_event_loop()
        self._conn = await loop.run_in_executor(
            None,
            lambda: sqlite3.connect(self._path, check_same_thread=False),
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._conn is not None:
            self._conn.close()

    async def execute(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> sqlite3.Cursor:
        if self._conn is None:  # pragma: no cover - defensive guard
            raise RuntimeError("sqlite connection not initialized")
        translated = re.sub(r"\$\d+", "?", query)
        loop = asyncio.get_event_loop()
        cursor = await loop.run_in_executor(None, lambda: self._conn.execute(translated, params))
        self._conn.commit()
        return cursor

    async def fetch(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> list[dict[str, Any]]:
        cursor = await self.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    async def fetchrow(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> dict[str, Any] | None:
        cursor = await self.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None


@asynccontextmanager
async def get_connection():
    """Yield an async connection using PostgreSQL when available, SQLite otherwise."""

    if PLATFORM.db_engine == "postgres":
        try:
            import asyncpg

            dsn = os.environ.get("DATABASE_URL", "postgresql://nova:nova@localhost/nova")
            conn = await asyncpg.connect(dsn)
            try:
                yield conn
            finally:
                await conn.close()
            return
        except ImportError:
            pass

    db_path = os.path.join(PLATFORM.nova_dir, "nova.db")
    os.makedirs(PLATFORM.nova_dir, exist_ok=True)
    async with _SQLiteConn(db_path) as conn:
        yield conn


async def init_db() -> None:
    """Initialize the portable fallback database."""

    if PLATFORM.db_engine == "postgres":
        return

    async with get_connection() as conn:
        schema = """
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            action TEXT NOT NULL,
            verdict TEXT NOT NULL,
            score INTEGER,
            reason TEXT,
            hash TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            rules TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(agent_id, key)
        );
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            workspace TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        for statement in schema.split(";"):
            statement = statement.strip()
            if statement:
                await conn.execute(statement)
