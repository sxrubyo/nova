"""Formatting helpers for CLI and status output."""

from __future__ import annotations

from datetime import timedelta

from nova.constants import NOVA_ASCII_BANNER


def banner() -> str:
    """Return the Nova startup banner."""

    return NOVA_ASCII_BANNER.strip("\n")


def human_duration(seconds: float) -> str:
    """Format seconds as a short human-readable duration."""

    return str(timedelta(seconds=int(seconds)))
