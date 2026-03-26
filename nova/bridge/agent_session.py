"""Connected agent session state."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class AgentSession:
    session_id: str
    agent_id: str
    api_key: str
    websocket: Any
    capabilities: list[str] = field(default_factory=list)
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    missed_heartbeats: int = 0
    queue: deque[dict] = field(default_factory=lambda: deque(maxlen=100))
