"""Loop detection based on Jaccard similarity."""

from __future__ import annotations

from collections import defaultdict, deque

from nova.types import LoopCheckResult
from nova.utils.text import flatten_payload, jaccard_similarity


class LoopDetector:
    """Detect repeated agent behavior over a short recent window."""

    def __init__(self) -> None:
        self._history: defaultdict[str, deque[str]] = defaultdict(lambda: deque(maxlen=10))

    async def check(
        self,
        agent_id: str,
        current_action: str,
        similarity_threshold: float = 0.85,
    ) -> LoopCheckResult:
        history = self._history[agent_id]
        similarities = [jaccard_similarity(current_action, previous) for previous in history]
        repeated = sum(1 for similarity in similarities if similarity >= similarity_threshold)
        max_similarity = max(similarities, default=0.0)
        history.append(current_action)
        return LoopCheckResult(
            is_loop=repeated >= 5,
            similarity=max_similarity,
            repeated_actions=repeated,
        )
