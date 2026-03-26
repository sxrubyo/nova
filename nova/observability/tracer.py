"""Request tracing helpers backed by contextvars."""

from __future__ import annotations

from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(value: str | None) -> None:
    """Attach a request id to the current task context."""

    request_id_var.set(value)


def get_request_id() -> str | None:
    """Fetch the current request id."""

    return request_id_var.get()
