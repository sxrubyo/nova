"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base declarative class."""


class WorkspaceModel(Base):
    """Workspace storage model."""

    __tablename__ = "nova_runtime_workspaces"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(32), default="free", nullable=False)
    quota_monthly: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    usage_this_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rules: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    thresholds: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    risk_profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    api_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    owner_email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="admin", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    agents: Mapped[list["AgentModel"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class AgentModel(Base):
    """Agent storage model."""

    __tablename__ = "nova_runtime_agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("nova_runtime_workspaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    evaluation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    workspace: Mapped["WorkspaceModel"] = relationship(back_populates="agents")


class EvaluationModel(Base):
    """Evaluation storage model."""

    __tablename__ = "nova_runtime_evaluations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("nova_runtime_agents.id", ondelete="CASCADE"), nullable=False)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("nova_runtime_workspaces.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[float] = mapped_column(nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LedgerRecordModel(Base):
    """Immutable ledger storage model."""

    __tablename__ = "nova_runtime_ledger_records"

    action_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    eval_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    agent_id: Mapped[str] = mapped_column(ForeignKey("nova_runtime_agents.id", ondelete="CASCADE"), nullable=False)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("nova_runtime_workspaces.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_summary: Mapped[str] = mapped_column(Text, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    sensitivity_flags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    anomalies: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    record_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MemoryModel(Base):
    """Persistent memory entry."""

    __tablename__ = "nova_runtime_memories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("nova_runtime_agents.id", ondelete="CASCADE"), nullable=False)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("nova_runtime_workspaces.id", ondelete="CASCADE"), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    importance: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
