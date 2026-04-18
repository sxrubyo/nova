"""Timing helpers."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator


def monotonic_ms() -> float:
    """Return current monotonic time in milliseconds."""

    return time.monotonic() * 1000


@contextmanager
def stopwatch() -> Iterator[callable[[], float]]:
    """Yield a callable that returns elapsed milliseconds."""

    start = time.monotonic()
    yield lambda: (time.monotonic() - start) * 1000
