"""Heartbeat management."""

from __future__ import annotations

from datetime import datetime, timezone

from nova.bridge.agent_session import AgentSession


class HeartbeatManager:
    """Updates and evaluates session heartbeat state."""

    def touch(self, session: AgentSession) -> None:
        session.last_heartbeat = datetime.now(timezone.utc)
        session.missed_heartbeats = 0

    def missed(self, session: AgentSession) -> None:
        session.missed_heartbeats += 1

    def stale(self, session: AgentSession, max_missed: int = 3) -> bool:
        return session.missed_heartbeats >= max_missed
