"""Typed models used across the Nova OS runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DecisionAction(str, Enum):
    """High-level decision emitted by the evaluation pipeline."""

    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


class RiskLevel(str, Enum):
    """Normalized risk bands."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentStatus(str, Enum):
    """Lifecycle states for registered agents."""

    ACTIVE = "active"
    PAUSED = "paused"
    INACTIVE = "inactive"


class WorkspacePlan(str, Enum):
    """Workspace subscription tier."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class ProviderState(str, Enum):
    """Health state exposed by the gateway."""

    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNCONFIGURED = "unconfigured"


class MemoryType(str, Enum):
    """Categories of memory managed by Nova."""

    CORE = "core"
    EPISODIC = "episodic"
    WORKING = "working"


@dataclass(slots=True)
class WorkspaceThresholds:
    """Risk thresholds used by the decision engine."""

    auto_allow: int = 30
    escalate: int = 60
    auto_block: int = 80


@dataclass(slots=True)
class WorkspaceRules:
    """Explicit allow and deny rules for a workspace."""

    can_do: list[str] = field(default_factory=list)
    cannot_do: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorkspaceRiskProfile:
    """Workspace-level context used by risk calculations."""

    business_hours_start: int = 8
    business_hours_end: int = 18
    timezone: str = "UTC"
    sensitivity_bias: int = 0


@dataclass(slots=True)
class WorkspaceRecord:
    """Stored workspace definition."""

    id: str
    name: str
    slug: str
    plan: WorkspacePlan
    quota_monthly: int
    usage_this_month: int
    rules: WorkspaceRules = field(default_factory=WorkspaceRules)
    thresholds: WorkspaceThresholds = field(default_factory=WorkspaceThresholds)
    risk_profile: WorkspaceRiskProfile = field(default_factory=WorkspaceRiskProfile)
    api_key: str | None = None
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentRecord:
    """Registered agent metadata."""

    id: str
    workspace_id: str
    name: str
    model: str
    provider: str
    status: AgentStatus = AgentStatus.ACTIVE
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    evaluation_count: int = 0
    last_seen_at: datetime | None = None
    created_at: datetime | None = None
    workspace: WorkspaceRecord | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EvaluationRequest:
    """Incoming evaluation request from API or bridge."""

    agent_id: str
    workspace_id: str | None
    action: str
    payload: dict[str, Any]
    actor_id: str | None = None
    source: str = "api"
    request_id: str | None = None


@dataclass(slots=True)
class IntentAnalysis:
    """Result of parsing agent intent."""

    action_type: str
    target: str
    target_provider: str | None
    parameters: dict[str, Any]
    inferred_purpose: str
    confidence: float
    raw_action: str


@dataclass(slots=True)
class RuleValidationResult:
    """Outcome of evaluating workspace rules."""

    violated: bool
    rule_name: str | None
    severity: str = "none"
    detail: str = ""
    matched_can_do: bool = False


@dataclass(slots=True)
class SensitivityFinding:
    """A single sensitive-data match."""

    flag: str
    start: int
    end: int


@dataclass(slots=True)
class SensitivityResult:
    """Aggregated scan results over a payload."""

    flags: list[str] = field(default_factory=list)
    findings: list[SensitivityFinding] = field(default_factory=list)
    severity: str = "none"
    redacted_preview: str = ""


@dataclass(slots=True)
class LoopCheckResult:
    """Loop detection output."""

    is_loop: bool
    similarity: float
    repeated_actions: int


@dataclass(slots=True)
class BurstCheckResult:
    """Burst detection output."""

    is_burst: bool
    requests_in_window: int
    window_seconds: int


@dataclass(slots=True)
class RiskFactor:
    """One factor that contributed to a risk score."""

    name: str
    impact: float
    detail: str


@dataclass(slots=True)
class RiskScore:
    """Final risk scoring output."""

    value: int
    level: RiskLevel
    factors: list[RiskFactor] = field(default_factory=list)
    breakdown: dict[str, int] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Decision:
    """Decision engine output."""

    action: DecisionAction
    reason: str
    requires_human: bool = False
    policy_hits: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExecutionResult:
    """Result produced by the action executor."""

    provider: str | None
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0


@dataclass(slots=True)
class LedgerRecord:
    """Immutable ledger record."""

    action_id: str
    eval_id: str
    agent_id: str
    workspace_id: str
    action_type: str
    risk_score: int
    decision: str
    sensitivity_flags: list[str]
    anomalies: list[str]
    hash: str
    previous_hash: str | None
    timestamp: datetime
    payload_summary: str
    result: dict[str, Any] | None = None


@dataclass(slots=True)
class MemoryItem:
    """Stored memory entry."""

    id: str
    agent_id: str
    workspace_id: str
    memory_type: MemoryType
    key: str
    value: dict[str, Any]
    importance: int
    created_at: datetime
    expires_at: datetime | None = None


@dataclass(slots=True)
class ProviderHealth:
    """Live provider health data."""

    name: str
    status: ProviderState
    latency_ms: float
    cost_per_1k_tokens: float
    models: list[str]
    last_error: str | None = None


@dataclass(slots=True)
class LLMRequest:
    """Normalized gateway request."""

    messages: list[dict[str, Any]]
    model: str | None = None
    provider: str | None = None
    timeout: float | None = None
    cost_target: str | None = None
    latency_target: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LLMResponse:
    """Normalized gateway response."""

    provider: str
    model: str
    content: str
    latency_ms: float
    raw: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvaluationContext:
    """Mutable state carried through the evaluation pipeline."""

    eval_id: str
    request: EvaluationRequest
    intent: IntentAnalysis | None = None
    sensitivity: SensitivityResult | None = None
    risk_score: RiskScore | None = None
    decision: Decision | None = None
    anomalies: list[str] = field(default_factory=list)
    violations: list[RuleValidationResult] = field(default_factory=list)


@dataclass(slots=True)
class EvaluationResult:
    """Final response emitted by the evaluation pipeline."""

    eval_id: str
    status: str
    decision: Decision
    risk_score: RiskScore
    intent_analysis: IntentAnalysis
    sensitivity: SensitivityResult
    anomalies: list[str]
    ledger_hash: str | None
    execution_result: ExecutionResult | None
    duration_ms: float
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SystemStatus:
    """Aggregated kernel status."""

    status: str
    version: str
    uptime_seconds: float
    memory_usage_mb: float
    active_agents: int
    subsystems: dict[str, str]
    providers: list[ProviderHealth] = field(default_factory=list)
    timestamp: datetime | None = None
