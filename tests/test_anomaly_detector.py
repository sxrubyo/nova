"""Anomaly detector tests."""

from __future__ import annotations

import pytest

from nova.security.burst_detector import BurstDetector
from nova.security.loop_detector import LoopDetector


@pytest.mark.asyncio
async def test_burst_detection() -> None:
    detector = BurstDetector()
    result = None
    for _ in range(60):
        result = await detector.check("agent-1", window_seconds=60, threshold=50)
    assert result is not None
    assert result.is_burst is True


@pytest.mark.asyncio
async def test_loop_detection() -> None:
    detector = LoopDetector()
    result = None
    for _ in range(6):
        result = await detector.check("agent-1", "send email to alice@example.com", similarity_threshold=0.85)
    assert result is not None
    assert result.is_loop is True


@pytest.mark.asyncio
async def test_normal_traffic() -> None:
    detector = LoopDetector()
    first = await detector.check("agent-1", "send email", similarity_threshold=0.85)
    second = await detector.check("agent-1", "query database", similarity_threshold=0.85)
    assert first.is_loop is False
    assert second.is_loop is False
