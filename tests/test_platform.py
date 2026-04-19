"""Tests for platform portability helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_platform_detect() -> None:
    from nova.platform import PlatformInfo, detect

    platform_info = detect()
    assert isinstance(platform_info, PlatformInfo)
    assert platform_info.type in ("termux", "linux", "macos", "windows", "unknown")
    assert os.path.isabs(platform_info.nova_dir)
    assert platform_info.db_engine in ("postgres", "sqlite")
    assert platform_info.process_manager in ("systemd", "pm2", "screen", "nohup")


def test_db_engine_fallback() -> None:
    from nova.platform import detect

    platform_info = detect()
    if not platform_info.has_postgres:
        assert platform_info.db_engine == "sqlite"


def test_explicit_postgres_url_forces_postgres_engine(monkeypatch) -> None:
    import nova.platform as platform_module

    original_which = platform_module.shutil.which
    monkeypatch.setenv("NOVA_DB_URL", "postgresql+asyncpg://user:pass@db:5432/nova")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(
        platform_module.shutil,
        "which",
        lambda binary: None if binary == "pg_isready" else original_which(binary),
    )

    platform_info = platform_module.detect()

    assert platform_info.has_postgres is True
    assert platform_info.db_engine == "postgres"


def test_nova_dir_writable() -> None:
    from nova.platform import PLATFORM

    os.makedirs(PLATFORM.nova_dir, exist_ok=True)
    test_file = os.path.join(PLATFORM.nova_dir, ".write_test")
    with open(test_file, "w", encoding="utf-8"):
        pass
    os.remove(test_file)


def test_lru_cache() -> None:
    from nova.memory.memory_engine import LRUMemoryCache

    cache = LRUMemoryCache(maxsize=5)
    for index in range(10):
        cache.put(str(index), index)

    assert cache.size == 5
    assert cache.get("5") == 5
    assert cache.get("0") is None
    assert list(cache.keys()) == ["6", "7", "8", "9", "5"]


if __name__ == "__main__":
    test_platform_detect()
    test_db_engine_fallback()
    test_nova_dir_writable()
    test_lru_cache()
    print("All tests passed.")
