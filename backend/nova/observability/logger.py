"""Structured logging setup."""

from __future__ import annotations

import json
import logging
import sys

try:
    import structlog
except ImportError:  # pragma: no cover - host compatibility fallback
    structlog = None

from nova.config import NovaConfig


class _CompatLogger:
    """Compat wrapper so stdlib logging can accept structlog-style kwargs."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def _emit(self, level: int, event: str, **kwargs: object) -> None:
        if kwargs:
            payload = " ".join(
                f"{key}={json.dumps(value, default=str, ensure_ascii=True)}"
                for key, value in sorted(kwargs.items())
            )
            self._logger.log(level, "%s %s", event, payload)
            return
        self._logger.log(level, "%s", event)

    def debug(self, event: str, **kwargs: object) -> None:
        self._emit(logging.DEBUG, event, **kwargs)

    def info(self, event: str, **kwargs: object) -> None:
        self._emit(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: object) -> None:
        self._emit(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs: object) -> None:
        self._emit(logging.ERROR, event, **kwargs)


def configure_logging(config: NovaConfig):
    """Configure stdlib and structlog once and return the root Nova logger."""

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(message)s" if config.log_format == "json" else "%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
        force=True,
    )
    if structlog is None:
        return _CompatLogger(logging.getLogger("nova"))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
            if config.log_format == "json"
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, config.log_level.upper(), logging.INFO)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger("nova")


def get_logger(name: str = "nova"):
    """Return a named logger."""

    if structlog is None:
        return _CompatLogger(logging.getLogger(name))
    return structlog.get_logger(name)
