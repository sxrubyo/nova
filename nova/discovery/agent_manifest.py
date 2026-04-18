"""Shared discovery and connector models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class DetectionEvidence:
    """One signal that contributed to a discovery match."""

    method: str
    detail: str
    confidence: float


@dataclass(slots=True)
class DiscoveredAgent:
    """Normalized view of a discovered runtime agent or tool."""

    agent_key: str
    fingerprint_key: str
    name: str
    type: str
    icon: str = "cpu"
    color: str = "#6B7280"
    confidence: float = 0.0
    detection_method: str = ""
    detection_methods: list[str] = field(default_factory=list)
    evidence: list[DetectionEvidence] = field(default_factory=list)
    version: str | None = None
    status: str = "discovered"
    discovered_at: datetime | None = None
    last_seen_at: datetime | None = None
    is_running: bool = False
    is_healthy: bool | None = None
    pid: int | None = None
    port: int | None = None
    ports: list[int] = field(default_factory=list)
    binary_path: str | None = None
    config_path: str | None = None
    config_paths: list[str] = field(default_factory=list)
    raw_config: str | None = None
    parsed_config: dict[str, Any] | None = None
    container_id: str | None = None
    container_name: str | None = None
    env_vars: list[str] = field(default_factory=list)
    process_info: dict[str, Any] = field(default_factory=dict)
    fingerprint: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    risk_profile: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    nova_id: str | None = None

    def add_evidence(self, method: str, detail: str, confidence: float) -> None:
        """Append evidence while keeping the method list unique."""

        if method not in self.detection_methods:
            self.detection_methods.append(method)
        self.evidence.append(DetectionEvidence(method=method, detail=detail, confidence=confidence))
        self.confidence = max(self.confidence, confidence)

    def merge(self, other: "DiscoveredAgent") -> None:
        """Merge duplicate findings for the same logical agent."""

        for evidence in other.evidence:
            self.add_evidence(evidence.method, evidence.detail, evidence.confidence)
        self.confidence = min(1.0, self.confidence + (0.05 * max(len(self.detection_methods) - 1, 0)))
        self.is_running = self.is_running or other.is_running
        self.is_healthy = other.is_healthy if other.is_healthy is not None else self.is_healthy
        self.pid = self.pid or other.pid
        self.port = self.port or other.port
        self.version = self.version or other.version
        self.binary_path = self.binary_path or other.binary_path
        self.config_path = self.config_path or other.config_path
        self.raw_config = self.raw_config or other.raw_config
        self.parsed_config = self.parsed_config or other.parsed_config
        self.container_id = self.container_id or other.container_id
        self.container_name = self.container_name or other.container_name
        self.last_seen_at = other.last_seen_at or self.last_seen_at
        self.status = other.status if other.status != "discovered" else self.status
        self.process_info = {**self.process_info, **other.process_info}
        self.metadata = {**self.metadata, **other.metadata}
        self.capabilities = self.capabilities or other.capabilities
        self.risk_profile = self.risk_profile or other.risk_profile
        self.ports = sorted({*self.ports, *other.ports, *([self.port] if self.port else []), *([other.port] if other.port else [])})
        self.config_paths = sorted({*self.config_paths, *other.config_paths, *([self.config_path] if self.config_path else []), *([other.config_path] if other.config_path else [])})
        self.env_vars = sorted({*self.env_vars, *other.env_vars})


@dataclass(slots=True)
class AgentTask:
    """Connector execution request."""

    prompt: str
    model: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    approval_mode: str = "suggest"
    working_directory: str | None = None
    timeout: int | None = 300


@dataclass(slots=True)
class TaskResult:
    """Connector execution result."""

    success: bool
    output: Any = None
    error: str | None = None
    exit_code: int | None = None
    status_code: int | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ConnectionResult:
    """Outcome of connecting Nova to a discovered or managed agent."""

    success: bool
    agent_key: str | None = None
    agent_id: str | None = None
    connection_type: str | None = None
    connector: str | None = None
    capabilities: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(slots=True)
class HealthStatus:
    """Best-effort health snapshot."""

    ok: bool
    status: str = "unknown"
    detail: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class AgentLogEntry:
    """Portable log record returned by connectors."""

    timestamp: str
    level: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)
