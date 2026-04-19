"""Logging compatibility regressions."""

from __future__ import annotations

import logging

from nova.config import NovaConfig
from nova.observability.logger import configure_logging


def test_configure_logging_quiets_http_clients_by_default(tmp_path) -> None:
    config = NovaConfig(
        NOVA_DB_URL=f"sqlite+aiosqlite:///{tmp_path / 'nova-logging.db'}",
        NOVA_WORKSPACE_ROOT=tmp_path,
        NOVA_DATA_DIR=tmp_path / "data",
    )

    configure_logging(config)

    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
