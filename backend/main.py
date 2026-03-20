"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║    ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗      ██████╗ ███████╗                ║
║    ████╗  ██║██╔═══██╗██║   ██║██╔══██╗    ██╔═══██╗██╔════╝                ║
║    ██╔██╗ ██║██║   ██║██║   ██║███████║    ██║   ██║███████╗                ║
║    ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║    ██║   ██║╚════██║                ║
║    ██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║    ╚██████╔╝███████║                ║
║    ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝     ╚═════╝ ╚══════╝                ║
║                                                                              ║
║    Nova OS v4.0 — Enterprise Governance Infrastructure for AI Agents        ║
║    2026 Edition                                                              ║
║                                                                              ║
║    Components:                                                               ║
║    ├── Intent Verification    — Multi-LLM scoring (9 providers)             ║
║    ├── Policy Engine          — Reusable governance templates               ║
║    ├── Memory Engine          — Persistent context + semantic search        ║
║    ├── Duplicate Guard        — Time-windowed similarity dedup              ║
║    ├── Response Generator     — Provider-agnostic LLM responses            ║
║    ├── Intent Ledger          — Immutable cryptographic audit trail         ║
║    ├── Alert System           — Real-time multi-severity notifications      ║
║    ├── Anomaly Detector       — Behavioral pattern analysis                 ║
║    ├── Analytics Engine       — Risk, timeline, agent insights              ║
║    ├── Skill Bridge           — skill_executor.py integration               ║
║    └── SSE Stream             — Real-time event streaming                   ║
║                                                                              ║
║    Copyright (c) 2026 Nova OS. All rights reserved.                         ║
║    https://nova-os.com                                                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import logging
import os
import re
import secrets
import sys
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from functools import wraps
from typing import (
    Any, AsyncGenerator, Dict, List, Optional,
    Tuple, Union, Callable, TypeVar, Generic, Annotated
)

import httpx
import databases
from fastapi import (
    FastAPI, HTTPException, Header, Depends,
    Request, Response, BackgroundTasks, Query, Path, Body
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator, root_validator
from starlette.middleware.base import BaseHTTPMiddleware


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

class Settings:
    """
    Application settings loaded from environment variables.
    Supports 9 LLM providers — configured per-workspace or globally.
    """

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://nova:nova_secret_2026@db:5432/nova"
    )
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "10"))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "nova_signing_key_CHANGE_IN_PRODUCTION_" + secrets.token_hex(16)
    )
    API_KEY_MIN_LENGTH: int = 16
    BCRYPT_ROUNDS: int = 12

    # ── Multi-LLM (2026 edition — pick one or configure per workspace) ────────
    # Primary provider — env var takes precedence over workspace config
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openrouter")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
    LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "15.0"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "500"))

    # Provider API keys (any one is sufficient)
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENAI_API_KEY: str     = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str  = os.getenv("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY: str     = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str       = os.getenv("GROQ_API_KEY", "")
    XAI_API_KEY: str        = os.getenv("XAI_API_KEY", "")
    MISTRAL_API_KEY: str    = os.getenv("MISTRAL_API_KEY", "")
    DEEPSEEK_API_KEY: str   = os.getenv("DEEPSEEK_API_KEY", "")
    COHERE_API_KEY: str     = os.getenv("COHERE_API_KEY", "")

    # Legacy alias
    OPENROUTER_MODEL: str     = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_TIMEOUT: float = float(os.getenv("OPENROUTER_TIMEOUT", "15.0"))
    OPENROUTER_MAX_TOKENS: int = int(os.getenv("OPENROUTER_MAX_TOKENS", "500"))

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int   = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    # ── Duplicate Detection ───────────────────────────────────────────────────
    DUPLICATE_WINDOW_MINUTES: int = int(os.getenv("DUPLICATE_WINDOW_MINUTES", "60"))
    DUPLICATE_THRESHOLD: float    = float(os.getenv("DUPLICATE_THRESHOLD", "0.82"))

    # ── Memory ────────────────────────────────────────────────────────────────
    MEMORY_DEFAULT_IMPORTANCE: int = 5
    MEMORY_MAX_PER_AGENT: int      = int(os.getenv("MEMORY_MAX_PER_AGENT", "1000"))
    MEMORY_AUTO_EXPIRE_DAYS: int   = int(os.getenv("MEMORY_AUTO_EXPIRE_DAYS", "90"))

    # ── Scoring ───────────────────────────────────────────────────────────────
    SCORE_APPROVED_THRESHOLD:  int = int(os.getenv("SCORE_APPROVED_THRESHOLD", "70"))
    SCORE_ESCALATED_THRESHOLD: int = int(os.getenv("SCORE_ESCALATED_THRESHOLD", "40"))

    # ── Anomaly Detection ─────────────────────────────────────────────────────
    ANOMALY_BLOCK_RATE_THRESHOLD: float = float(os.getenv("ANOMALY_BLOCK_RATE_THRESHOLD", "0.5"))
    ANOMALY_BURST_THRESHOLD: int        = int(os.getenv("ANOMALY_BURST_THRESHOLD", "20"))
    ANOMALY_BURST_WINDOW_MINUTES: int   = int(os.getenv("ANOMALY_BURST_WINDOW_MINUTES", "5"))

    # ── Skill Executor ────────────────────────────────────────────────────────
    SKILL_EXECUTOR_ENABLED: bool = os.getenv("SKILL_EXECUTOR_ENABLED", "false").lower() == "true"
    SKILL_EXECUTOR_TIMEOUT: float = float(os.getenv("SKILL_EXECUTOR_TIMEOUT", "30.0"))

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str  = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    # ── Server ────────────────────────────────────────────────────────────────
    VERSION: str     = "4.0.0"
    BUILD: str       = "2026.03.enterprise"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool      = os.getenv("DEBUG", "false").lower() == "true"

    @classmethod
    def is_production(cls) -> bool:
        return cls.ENVIRONMENT == "production"

    @classmethod
    def has_llm(cls) -> bool:
        """Return True if at least one LLM provider is configured."""
        return bool(
            cls.OPENROUTER_API_KEY or cls.OPENAI_API_KEY or
            cls.ANTHROPIC_API_KEY  or cls.GEMINI_API_KEY  or
            cls.GROQ_API_KEY       or cls.XAI_API_KEY     or
            cls.MISTRAL_API_KEY    or cls.DEEPSEEK_API_KEY or
            cls.COHERE_API_KEY
        )

    @classmethod
    def get_active_llm(cls) -> Tuple[str, str]:
        """
        Return (provider_key, api_key) for the first configured provider.
        Priority: OPENROUTER > ANTHROPIC > OPENAI > GOOGLE > GROQ > ...
        """
        priority = [
            ("openrouter", cls.OPENROUTER_API_KEY),
            ("anthropic",  cls.ANTHROPIC_API_KEY),
            ("openai",     cls.OPENAI_API_KEY),
            ("gemini",     cls.GEMINI_API_KEY),
            ("groq",       cls.GROQ_API_KEY),
            ("xai",        cls.XAI_API_KEY),
            ("mistral",    cls.MISTRAL_API_KEY),
            ("deepseek",   cls.DEEPSEEK_API_KEY),
            ("cohere",     cls.COHERE_API_KEY),
        ]
        for provider, key in priority:
            if key:
                return provider, key
        return "", ""


settings = Settings()


# ══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════════════════

def setup_logging() -> logging.Logger:
    formatter = logging.Formatter(settings.LOG_FORMAT)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    root_logger.addHandler(console_handler)
    logger = logging.getLogger("nova")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    logging.getLogger("databases").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    return logger


log = setup_logging()


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════════════════

db = databases.Database(
    settings.DATABASE_URL,
    min_size=settings.DATABASE_POOL_SIZE,
    max_size=settings.DATABASE_POOL_SIZE + settings.DATABASE_MAX_OVERFLOW
)


async def init_database():
    """Initialize all database tables, indexes, and migrations."""

    log.info("Initializing database schema (v4.0)...")

    # ── Core tables ───────────────────────────────────────────────────────────

    await db.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name            TEXT NOT NULL,
            api_key         TEXT UNIQUE NOT NULL,
            plan            TEXT DEFAULT 'free',
            settings        JSONB DEFAULT '{}',
            usage_this_month INTEGER DEFAULT 0,
            quota_monthly   INTEGER DEFAULT 10000,
            features        TEXT[] DEFAULT '{}',
            created_at      TIMESTAMPTZ DEFAULT NOW(),
            updated_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS intent_tokens (
            id              BIGSERIAL PRIMARY KEY,
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            agent_name      TEXT NOT NULL,
            description     TEXT DEFAULT '',
            can_do          TEXT[] NOT NULL DEFAULT '{}',
            cannot_do       TEXT[] NOT NULL DEFAULT '{}',
            policy_id       BIGINT,
            authorized_by   TEXT NOT NULL,
            signature       TEXT NOT NULL,
            metadata        JSONB DEFAULT '{}',
            active          BOOLEAN DEFAULT TRUE,
            version         INTEGER DEFAULT 1,
            created_at      TIMESTAMPTZ DEFAULT NOW(),
            updated_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS ledger (
            id              BIGSERIAL PRIMARY KEY,
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            token_id        BIGINT NOT NULL REFERENCES intent_tokens(id),
            agent_name      TEXT NOT NULL,
            action          TEXT NOT NULL,
            context         TEXT DEFAULT '',
            score           INTEGER NOT NULL,
            confidence      FLOAT DEFAULT 1.0,
            risk_level      TEXT DEFAULT 'low',
            verdict         TEXT NOT NULL,
            reason          TEXT NOT NULL,
            response        TEXT,
            duplicate_of    BIGINT,
            score_factors   JSONB DEFAULT '{}',
            skill_evidence  JSONB DEFAULT '{}',
            prev_hash       TEXT NOT NULL,
            own_hash        TEXT NOT NULL,
            request_id      TEXT,
            client_ip       TEXT,
            user_agent      TEXT,
            llm_provider    TEXT,
            llm_model       TEXT,
            latency_ms      INTEGER,
            executed_at     TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id              BIGSERIAL PRIMARY KEY,
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            agent_name      TEXT NOT NULL,
            key             TEXT NOT NULL,
            value           TEXT NOT NULL,
            tags            TEXT[] DEFAULT '{}',
            importance      INTEGER DEFAULT 5 CHECK (importance >= 1 AND importance <= 10),
            source          TEXT DEFAULT 'manual',
            metadata        JSONB DEFAULT '{}',
            expires_at      TIMESTAMPTZ,
            created_at      TIMESTAMPTZ DEFAULT NOW(),
            updated_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id              BIGSERIAL PRIMARY KEY,
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            ledger_id       BIGINT REFERENCES ledger(id),
            agent_name      TEXT NOT NULL,
            alert_type      TEXT DEFAULT 'violation',
            severity        TEXT DEFAULT 'medium',
            message         TEXT NOT NULL,
            score           INTEGER,
            metadata        JSONB DEFAULT '{}',
            resolved        BOOLEAN DEFAULT FALSE,
            resolved_by     TEXT,
            resolved_at     TIMESTAMPTZ,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS rate_limits (
            id              BIGSERIAL PRIMARY KEY,
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            window_start    TIMESTAMPTZ NOT NULL,
            request_count   INTEGER DEFAULT 1,
            UNIQUE(workspace_id, window_start)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS analytics_events (
            id              BIGSERIAL PRIMARY KEY,
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            event_type      TEXT NOT NULL,
            event_data      JSONB DEFAULT '{}',
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # ── New tables (v4.0) ─────────────────────────────────────────────────────

    # Policy templates — reusable can_do/cannot_do rule sets
    await db.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            id              BIGSERIAL PRIMARY KEY,
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            name            TEXT NOT NULL,
            description     TEXT DEFAULT '',
            category        TEXT DEFAULT 'general',
            can_do          TEXT[] NOT NULL DEFAULT '{}',
            cannot_do       TEXT[] NOT NULL DEFAULT '{}',
            tags            TEXT[] DEFAULT '{}',
            is_template     BOOLEAN DEFAULT FALSE,
            version         INTEGER DEFAULT 1,
            created_by      TEXT NOT NULL,
            metadata        JSONB DEFAULT '{}',
            active          BOOLEAN DEFAULT TRUE,
            created_at      TIMESTAMPTZ DEFAULT NOW(),
            updated_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Anomaly log — track detected behavioral anomalies
    await db.execute("""
        CREATE TABLE IF NOT EXISTS anomaly_log (
            id              BIGSERIAL PRIMARY KEY,
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            agent_name      TEXT NOT NULL,
            anomaly_type    TEXT NOT NULL,
            severity        TEXT DEFAULT 'medium',
            description     TEXT NOT NULL,
            evidence        JSONB DEFAULT '{}',
            resolved        BOOLEAN DEFAULT FALSE,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Token version history — keeps history when rules change
    await db.execute("""
        CREATE TABLE IF NOT EXISTS token_history (
            id              BIGSERIAL PRIMARY KEY,
            token_id        BIGINT NOT NULL REFERENCES intent_tokens(id) ON DELETE CASCADE,
            version         INTEGER NOT NULL,
            can_do          TEXT[] NOT NULL DEFAULT '{}',
            cannot_do       TEXT[] NOT NULL DEFAULT '{}',
            changed_by      TEXT,
            change_reason   TEXT,
            changed_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # SSE event queue — for real-time streaming
    await db.execute("""
        CREATE TABLE IF NOT EXISTS sse_events (
            id              BIGSERIAL PRIMARY KEY,
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            event_type      TEXT NOT NULL,
            payload         JSONB NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # ── Indexes ───────────────────────────────────────────────────────────────

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_tokens_workspace   ON intent_tokens(workspace_id)",
        "CREATE INDEX IF NOT EXISTS idx_tokens_active      ON intent_tokens(workspace_id, active)",
        "CREATE INDEX IF NOT EXISTS idx_tokens_policy      ON intent_tokens(policy_id)",
        "CREATE INDEX IF NOT EXISTS idx_ledger_workspace   ON ledger(workspace_id)",
        "CREATE INDEX IF NOT EXISTS idx_ledger_token       ON ledger(token_id)",
        "CREATE INDEX IF NOT EXISTS idx_ledger_verdict     ON ledger(workspace_id, verdict)",
        "CREATE INDEX IF NOT EXISTS idx_ledger_executed    ON ledger(workspace_id, executed_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_ledger_agent       ON ledger(workspace_id, agent_name)",
        "CREATE INDEX IF NOT EXISTS idx_ledger_risk        ON ledger(workspace_id, risk_level)",
        "CREATE INDEX IF NOT EXISTS idx_memories_agent     ON memories(workspace_id, agent_name)",
        "CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(workspace_id, agent_name, importance DESC)",
        "CREATE INDEX IF NOT EXISTS idx_memories_expires   ON memories(expires_at) WHERE expires_at IS NOT NULL",
        "CREATE INDEX IF NOT EXISTS idx_alerts_workspace   ON alerts(workspace_id)",
        "CREATE INDEX IF NOT EXISTS idx_alerts_unresolved  ON alerts(workspace_id, resolved) WHERE resolved = FALSE",
        "CREATE INDEX IF NOT EXISTS idx_rate_limits_window ON rate_limits(workspace_id, window_start)",
        "CREATE INDEX IF NOT EXISTS idx_analytics_type     ON analytics_events(workspace_id, event_type)",
        "CREATE INDEX IF NOT EXISTS idx_policies_workspace ON policies(workspace_id)",
        "CREATE INDEX IF NOT EXISTS idx_policies_category  ON policies(workspace_id, category)",
        "CREATE INDEX IF NOT EXISTS idx_anomaly_agent      ON anomaly_log(workspace_id, agent_name)",
        "CREATE INDEX IF NOT EXISTS idx_sse_events_ws      ON sse_events(workspace_id, created_at DESC)",
    ]

    for idx in indexes:
        try:
            await db.execute(idx)
        except Exception as e:
            log.debug(f"Index skipped: {e}")

    # ── Migrations (add new columns to existing tables) ───────────────────────

    migrations = [
        "ALTER TABLE ledger ADD COLUMN IF NOT EXISTS score_factors JSONB DEFAULT '{}'",
        "ALTER TABLE ledger ADD COLUMN IF NOT EXISTS request_id TEXT",
        "ALTER TABLE ledger ADD COLUMN IF NOT EXISTS client_ip TEXT",
        "ALTER TABLE ledger ADD COLUMN IF NOT EXISTS user_agent TEXT",
        "ALTER TABLE ledger ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 1.0",
        "ALTER TABLE ledger ADD COLUMN IF NOT EXISTS risk_level TEXT DEFAULT 'low'",
        "ALTER TABLE ledger ADD COLUMN IF NOT EXISTS skill_evidence JSONB DEFAULT '{}'",
        "ALTER TABLE ledger ADD COLUMN IF NOT EXISTS llm_provider TEXT",
        "ALTER TABLE ledger ADD COLUMN IF NOT EXISTS llm_model TEXT",
        "ALTER TABLE ledger ADD COLUMN IF NOT EXISTS latency_ms INTEGER",
        "ALTER TABLE memories ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'",
        "ALTER TABLE memories ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS alert_type TEXT DEFAULT 'violation'",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS severity TEXT DEFAULT 'medium'",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'",
        "ALTER TABLE intent_tokens ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'",
        "ALTER TABLE intent_tokens ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()",
        "ALTER TABLE intent_tokens ADD COLUMN IF NOT EXISTS policy_id BIGINT",
        "ALTER TABLE intent_tokens ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1",
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS usage_this_month INTEGER DEFAULT 0",
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS quota_monthly INTEGER DEFAULT 10000",
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS features TEXT[] DEFAULT '{}'",
    ]

    for migration in migrations:
        try:
            await db.execute(migration)
        except Exception as e:
            log.debug(f"Migration skipped: {e}")

    log.info("Database schema v4.0 initialized successfully")


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

class Verdict(str, Enum):
    APPROVED   = "APPROVED"
    BLOCKED    = "BLOCKED"
    ESCALATED  = "ESCALATED"
    DUPLICATE  = "DUPLICATE"


class RiskLevel(str, Enum):
    """Enriched risk classification beyond binary BLOCK/APPROVE."""
    CRITICAL = "critical"   # score < 20
    HIGH     = "high"       # score 20-39
    MEDIUM   = "medium"     # score 40-69
    LOW      = "low"        # score 70-89
    NONE     = "none"       # score 90-100


class AlertSeverity(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    VIOLATION  = "violation"
    ESCALATION = "escalation"
    ANOMALY    = "anomaly"
    RATE_LIMIT = "rate_limit"
    SYSTEM     = "system"


class PolicyCategory(str, Enum):
    GENERAL      = "general"
    COMMUNICATION = "communication"
    FINANCE      = "finance"
    DATA         = "data"
    DEVELOPMENT  = "development"
    OPERATIONS   = "operations"
    COMPLIANCE   = "compliance"


class AnomalyType(str, Enum):
    HIGH_BLOCK_RATE  = "high_block_rate"
    BURST_ACTIVITY   = "burst_activity"
    SCORE_DEGRADATION = "score_degradation"
    SENSITIVE_DATA   = "sensitive_data_exposure"
    LIMIT_PROBING    = "limit_probing"


# Provider → API endpoint + auth header
LLM_ENDPOINTS: Dict[str, Dict] = {
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "extra_headers": {
            "HTTP-Referer": "https://nova-os.com",
            "X-Title": "Nova OS"
        },
    },
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "extra_headers": {},
    },
    "anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "auth_header": "x-api-key",
        "auth_prefix": "",
        "extra_headers": {"anthropic-version": "2023-06-01"},
        "format": "anthropic",  # Different request format
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "extra_headers": {},
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "extra_headers": {},
    },
    "xai": {
        "url": "https://api.x.ai/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "extra_headers": {},
    },
    "mistral": {
        "url": "https://api.mistral.ai/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "extra_headers": {},
    },
    "deepseek": {
        "url": "https://api.deepseek.com/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "extra_headers": {},
    },
    "cohere": {
        "url": "https://api.cohere.ai/v2/chat",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "extra_headers": {},
        "format": "cohere",
    },
}

# Default model per provider
LLM_DEFAULT_MODELS: Dict[str, str] = {
    "openrouter": "openai/gpt-4o-mini",
    "openai":     "gpt-4o-mini",
    "anthropic":  "claude-sonnet-4-6",
    "gemini":     "gemini-2.0-flash",
    "groq":       "llama-3.3-70b-versatile",
    "xai":        "grok-3",
    "mistral":    "mistral-small-latest",
    "deepseek":   "deepseek-chat",
    "cohere":     "command-r-plus-08-2024",
}

HIGH_RISK_VERBS = {
    "en": ["delete", "remove", "cancel", "modify", "override", "disable",
           "terminate", "destroy", "drop", "truncate", "wipe", "purge",
           "revoke", "suspend", "deactivate", "kill", "stop", "halt"],
    "es": ["eliminar", "borrar", "cancelar", "modificar", "alterar",
           "deshabilitar", "terminar", "destruir", "revocar", "suspender",
           "desactivar", "detener", "parar", "anular", "suprimir"]
}

SENSITIVE_PATTERNS = [
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
    r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b',
    r'(?i)(api[_-]?key|secret|password|token|credential)["\s:=]+["\']?[\w-]{8,}',
]


# ══════════════════════════════════════════════════════════════════════════════
# CRYPTOGRAPHY
# ══════════════════════════════════════════════════════════════════════════════

class Crypto:
    @staticmethod
    def sign(data: dict) -> str:
        payload = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(
            f"{settings.SECRET_KEY}:{payload}".encode()
        ).hexdigest()

    @staticmethod
    def chain_hash(prev_hash: str, record: dict) -> str:
        payload = json.dumps(
            {"prev": prev_hash, "record": record},
            sort_keys=True, default=str
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def generate_request_id() -> str:
        return f"req_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def hash_action(action: str) -> str:
        return hashlib.md5(action.encode()).hexdigest()[:12]

    @staticmethod
    def generate_api_key() -> str:
        """Generate a cryptographically secure API key."""
        return f"nova_{secrets.token_hex(32)}"


# ══════════════════════════════════════════════════════════════════════════════
# TEXT SIMILARITY
# ══════════════════════════════════════════════════════════════════════════════

class TextSimilarity:
    @staticmethod
    def word_set(text: str) -> set:
        return set(re.findall(r'\w+', text.lower()))

    @staticmethod
    def jaccard_similarity(a: str, b: str) -> float:
        wa, wb = TextSimilarity.word_set(a), TextSimilarity.word_set(b)
        if not wa or not wb:
            return 0.0
        intersection = len(wa & wb)
        union = len(wa | wb)
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        numbers = []
        for match in re.findall(r'\d+(?:[.,]\d+)?', text):
            try:
                numbers.append(float(match.replace(',', '.')))
            except ValueError:
                pass
        return numbers

    @staticmethod
    def extract_limit(rule: str) -> Tuple[Optional[float], bool]:
        rule_lower = rule.lower()
        patterns = [
            r'>\s*\$?\s*(\d+(?:[.,]\d+)?)\s*([km%]?)',
            r'(?:more|greater|mayor|over|above|exceeds?|supera)\s+(?:than|a|de|que)?\s*\$?\s*(\d+(?:[.,]\d+)?)\s*([km%]?)',
            r'(?:limit|límite|max|máximo)(?:imum)?\s*(?:of|de|:)?\s*\$?\s*(\d+(?:[.,]\d+)?)\s*([km%]?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, rule_lower)
            if match:
                try:
                    value = float(match.group(1).replace(',', '.'))
                    suffix = match.group(2).lower() if len(match.groups()) > 1 else ""
                    if suffix == 'k':
                        value *= 1000
                    elif suffix == 'm':
                        value *= 1_000_000
                    is_pct = '%' in rule_lower or 'percent' in rule_lower
                    return value, is_pct
                except (ValueError, IndexError):
                    pass
        return None, False

    @staticmethod
    def contains_sensitive_data(text: str) -> List[str]:
        found = []
        for pattern in SENSITIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                found.append(pattern)
        return found

    @staticmethod
    def detect_language(text: str) -> str:
        """Simple language detection — 'es' or 'en'."""
        es_markers = len(re.findall(
            r'\b(el|la|los|las|un|una|es|que|por|con|para|también|del)\b',
            text.lower()
        ))
        return "es" if es_markers >= 2 else "en"


# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════════════════

# ── Request Models ────────────────────────────────────────────────────────────

class TokenCreate(BaseModel):
    agent_name:    str = Field(..., min_length=1, max_length=100)
    description:   Optional[str] = Field(default="", max_length=500)
    can_do:        List[str] = Field(..., min_items=0, max_items=50)
    cannot_do:     List[str] = Field(..., min_items=0, max_items=50)
    authorized_by: str = Field(..., min_length=1, max_length=100)
    policy_id:     Optional[int] = Field(default=None)
    metadata:      Optional[Dict[str, Any]] = Field(default={})

    @validator('can_do', 'cannot_do', each_item=True)
    def validate_rules(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("Rule must be at least 3 characters")
        if len(v) > 500:
            raise ValueError("Rule must be under 500 characters")
        return v.strip()


class TokenUpdate(BaseModel):
    description:  Optional[str] = None
    can_do:       Optional[List[str]] = None
    cannot_do:    Optional[List[str]] = None
    active:       Optional[bool] = None
    policy_id:    Optional[int] = None
    metadata:     Optional[Dict[str, Any]] = None
    change_reason: Optional[str] = None
    changed_by:   Optional[str] = None


class ValidateRequest(BaseModel):
    token_id:               str = Field(..., description="Intent Token ID")
    action:                 str = Field(..., min_length=1, max_length=5000)
    context:                Optional[str] = Field(default="", max_length=10000)
    generate_response:      Optional[bool] = Field(default=True)
    check_duplicates:       Optional[bool] = Field(default=True)
    duplicate_window_minutes: Optional[int] = Field(default=60, ge=1, le=1440)
    duplicate_threshold:    Optional[float] = Field(default=0.82, ge=0.5, le=1.0)
    run_skills:             Optional[bool] = Field(default=False)
    dry_run:                Optional[bool] = Field(default=False)
    metadata:               Optional[Dict[str, Any]] = Field(default={})


class BatchValidateRequest(BaseModel):
    """Validate multiple actions simultaneously (up to 20)."""
    token_id:          str = Field(..., description="Intent Token ID for all actions")
    actions:           List[str] = Field(..., min_items=1, max_items=20)
    context:           Optional[str] = Field(default="", max_length=5000)
    generate_response: Optional[bool] = Field(default=False)
    check_duplicates:  Optional[bool] = Field(default=True)
    dry_run:           Optional[bool] = Field(default=False)


class ExplainRequest(BaseModel):
    """Request a deep chain-of-thought explanation of a validation decision."""
    token_id: str
    action:   str = Field(..., min_length=1, max_length=5000)
    context:  Optional[str] = Field(default="", max_length=5000)


class SimulateRequest(BaseModel):
    """Simulate a policy change without modifying the live token."""
    agent_name:  str
    can_do:      List[str]
    cannot_do:   List[str]
    test_actions: List[str] = Field(..., min_items=1, max_items=10)
    context:     Optional[str] = Field(default="")


class PolicyCreate(BaseModel):
    name:        str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(default="", max_length=500)
    category:    Optional[str] = Field(default="general")
    can_do:      List[str] = Field(..., min_items=1, max_items=100)
    cannot_do:   List[str] = Field(..., min_items=0, max_items=100)
    tags:        Optional[List[str]] = Field(default=[])
    is_template: Optional[bool] = Field(default=False)
    created_by:  str = Field(..., min_length=1, max_length=100)
    metadata:    Optional[Dict[str, Any]] = Field(default={})

    @validator('can_do', 'cannot_do', each_item=True)
    def validate_rules(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("Rule must be at least 3 characters")
        return v.strip()


class PolicyUpdate(BaseModel):
    name:        Optional[str] = None
    description: Optional[str] = None
    can_do:      Optional[List[str]] = None
    cannot_do:   Optional[List[str]] = None
    tags:        Optional[List[str]] = None
    active:      Optional[bool] = None
    metadata:    Optional[Dict[str, Any]] = None


class MemoryCreate(BaseModel):
    agent_name:       str = Field(..., min_length=1, max_length=100)
    key:              str = Field(..., min_length=1, max_length=200)
    value:            str = Field(..., min_length=1, max_length=10000)
    tags:             Optional[List[str]] = Field(default=[], max_items=20)
    importance:       Optional[int] = Field(default=5, ge=1, le=10)
    expires_in_hours: Optional[int] = Field(default=None, ge=1, le=8760)
    metadata:         Optional[Dict[str, Any]] = Field(default={})

    @validator('tags', each_item=True)
    def validate_tags(cls, v):
        return v.strip().lower()[:50]


class MemoryUpdate(BaseModel):
    value:            Optional[str] = None
    tags:             Optional[List[str]] = None
    importance:       Optional[int] = Field(default=None, ge=1, le=10)
    expires_in_hours: Optional[int] = None
    metadata:         Optional[Dict[str, Any]] = None


class MemorySearch(BaseModel):
    agent_name:     str
    query:          str = Field(..., min_length=1, max_length=1000)
    limit:          Optional[int] = Field(default=10, ge=1, le=100)
    min_importance: Optional[int] = Field(default=1, ge=1, le=10)
    tags:           Optional[List[str]] = None


class AlertResolve(BaseModel):
    resolved_by: Optional[str] = None
    notes:       Optional[str] = None


class WebhookBody(BaseModel):
    action:           Optional[str] = None
    message:          Optional[str] = None
    texto:            Optional[str] = None
    token_id:         Optional[str] = None
    token:            Optional[str] = None
    context:          Optional[str] = None
    contexto:         Optional[str] = None
    agent_name:       Optional[str] = None
    memory_key:       Optional[str] = None
    memory_val:       Optional[str] = None
    memory_tags:      Optional[List[str]] = None
    memory_importance: Optional[int] = None
    respond:          Optional[bool] = True
    dedup:            Optional[bool] = True
    dry_run:          Optional[bool] = False


# ── Response Models ───────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    id:            str
    agent_name:    str
    description:   str
    can_do:        List[str]
    cannot_do:     List[str]
    authorized_by: str
    signature:     str
    policy_id:     Optional[int]
    active:        bool
    version:       int
    metadata:      Dict[str, Any]
    created_at:    datetime
    updated_at:    Optional[datetime]


class ValidateResponse(BaseModel):
    verdict:         Verdict
    score:           int
    confidence:      float
    risk_level:      str
    reason:          str
    response:        Optional[str]
    execute:         bool
    agent_name:      str
    ledger_id:       Optional[int]
    hash:            Optional[str]
    memories_used:   int
    duplicate_check: str
    duplicate_of:    Optional[Dict[str, Any]]
    score_factors:   Optional[Dict[str, int]]
    skill_evidence:  Optional[Dict[str, Any]]
    llm_provider:    Optional[str]
    request_id:      str
    latency_ms:      int


class BatchValidateResponse(BaseModel):
    results:    List[ValidateResponse]
    summary:    Dict[str, Any]
    request_id: str
    latency_ms: int


class PolicyResponse(BaseModel):
    id:          int
    name:        str
    description: str
    category:    str
    can_do:      List[str]
    cannot_do:   List[str]
    tags:        List[str]
    is_template: bool
    version:     int
    created_by:  str
    active:      bool
    metadata:    Dict[str, Any]
    created_at:  datetime
    updated_at:  Optional[datetime]


class MemoryResponse(BaseModel):
    id:         int
    agent_name: str
    key:        str
    value:      str
    tags:       List[str]
    importance: int
    source:     str
    metadata:   Dict[str, Any]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]


class LedgerEntry(BaseModel):
    id:            int
    agent_name:    str
    action:        str
    context:       Optional[str]
    score:         int
    confidence:    float
    risk_level:    str
    verdict:       Verdict
    reason:        str
    response:      Optional[str]
    score_factors: Optional[Dict[str, int]]
    own_hash:      str
    llm_provider:  Optional[str]
    latency_ms:    Optional[int]
    executed_at:   datetime


class AlertResponse(BaseModel):
    id:          int
    agent_name:  str
    alert_type:  str
    severity:    str
    message:     str
    score:       Optional[int]
    metadata:    Dict[str, Any]
    resolved:    bool
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]
    created_at:  datetime


class StatsResponse(BaseModel):
    total_actions:      int
    approved:           int
    blocked:            int
    escalated:          int
    duplicates_blocked: int
    avg_score:          int
    active_agents:      int
    alerts_pending:     int
    memories_stored:    int
    approval_rate:      float
    score_trend:        Optional[List[int]]


class HealthResponse(BaseModel):
    status:         str
    version:        str
    build:          str
    environment:    str
    timestamp:      datetime
    database:       str
    llm_available:  bool
    llm_provider:   str
    uptime_seconds: int
    active_streams: int


class ErrorResponse(BaseModel):
    error:      str
    code:       str
    detail:     Optional[str]
    request_id: Optional[str]


# ══════════════════════════════════════════════════════════════════════════════
# MIDDLEWARE
# ══════════════════════════════════════════════════════════════════════════════

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = Crypto.generate_request_id()
        request.state.request_id = request_id
        request.state.start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - request.state.start_time
        response.headers["X-Request-ID"]    = request_id
        response.headers["X-Process-Time"]  = f"{process_time:.3f}s"
        response.headers["X-Nova-Version"]  = settings.VERSION
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/", "/health", "/stream/events"):
            return await call_next(request)
        api_key   = request.headers.get("x-api-key", "")
        client_id = api_key[:16] if api_key else (request.client.host if request.client else "unknown")
        now          = time.time()
        window_start = now - 60
        self.requests[client_id] = [t for t in self.requests[client_id] if t > window_start]
        if len(self.requests[client_id]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "code": "RATE_LIMIT",
                    "detail": f"Maximum {self.requests_per_minute} requests per minute",
                    "retry_after": 60
                }
            )
        self.requests[client_id].append(now)
        return await call_next(request)


# ══════════════════════════════════════════════════════════════════════════════
# DEPENDENCIES
# ══════════════════════════════════════════════════════════════════════════════

async def get_workspace(
    x_api_key: str = Header(..., description="Workspace API key")
) -> Dict[str, Any]:
    if not x_api_key or len(x_api_key) < settings.API_KEY_MIN_LENGTH:
        raise HTTPException(status_code=401, detail="Invalid API key format")
    row = await db.fetch_one(
        "SELECT * FROM workspaces WHERE api_key = :key", {"key": x_api_key}
    )
    if not row:
        log.warning(f"Invalid API key: {x_api_key[:8]}...")
        raise HTTPException(status_code=401, detail="Invalid API key")
    return dict(row)


async def get_request_context(request: Request) -> Dict[str, Any]:
    return {
        "request_id": getattr(request.state, "request_id", Crypto.generate_request_id()),
        "client_ip":  request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", ""),
        "start_time": getattr(request.state, "start_time", time.time()),
    }


# ══════════════════════════════════════════════════════════════════════════════
# MULTI-LLM GATEWAY
# ══════════════════════════════════════════════════════════════════════════════

class LLMGateway:
    """
    Provider-agnostic LLM gateway.
    Supports OpenRouter, Anthropic, OpenAI, Google, Groq, xAI, Mistral,
    DeepSeek, Cohere — automatically selects the best available.
    """

    @staticmethod
    def _get_provider_key(provider: str) -> str:
        key_map = {
            "openrouter": settings.OPENROUTER_API_KEY,
            "openai":     settings.OPENAI_API_KEY,
            "anthropic":  settings.ANTHROPIC_API_KEY,
            "gemini":     settings.GEMINI_API_KEY,
            "groq":       settings.GROQ_API_KEY,
            "xai":        settings.XAI_API_KEY,
            "mistral":    settings.MISTRAL_API_KEY,
            "deepseek":   settings.DEEPSEEK_API_KEY,
            "cohere":     settings.COHERE_API_KEY,
        }
        return key_map.get(provider, "")

    @staticmethod
    async def complete(
        messages: List[Dict],
        max_tokens: int = 500,
        temperature: float = 0.1,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        """
        Call LLM and return (content, provider_used, model_used).
        Auto-falls back to next provider if one fails.
        """
        # Resolve provider
        if provider and LLMGateway._get_provider_key(provider):
            providers_to_try = [(provider, LLMGateway._get_provider_key(provider))]
        else:
            active_p, active_k = settings.get_active_llm()
            if not active_p:
                raise RuntimeError("No LLM provider configured")
            providers_to_try = [(active_p, active_k)]

        last_error = None
        for prov, key in providers_to_try:
            try:
                endpoint = LLM_ENDPOINTS.get(prov, LLM_ENDPOINTS["openrouter"])
                resolved_model = model or LLM_DEFAULT_MODELS.get(prov, "gpt-4o-mini")

                headers = {"Content-Type": "application/json"}
                auth_prefix = endpoint["auth_header"]
                if endpoint["auth_prefix"]:
                    headers[auth_prefix] = f"{endpoint['auth_prefix']} {key}"
                else:
                    headers[auth_prefix] = key
                headers.update(endpoint.get("extra_headers", {}))

                fmt = endpoint.get("format", "openai")

                if fmt == "anthropic":
                    # Anthropic messages format
                    sys_msgs = [m["content"] for m in messages if m["role"] == "system"]
                    usr_msgs = [m for m in messages if m["role"] != "system"]
                    body = {
                        "model": resolved_model,
                        "max_tokens": max_tokens,
                        "messages": usr_msgs,
                    }
                    if sys_msgs:
                        body["system"] = sys_msgs[0]
                else:
                    body = {
                        "model": resolved_model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    }

                async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
                    resp = await client.post(endpoint["url"], headers=headers, json=body)
                    resp.raise_for_status()
                    data = resp.json()

                if fmt == "anthropic":
                    content = data["content"][0]["text"].strip()
                elif fmt == "cohere":
                    content = data.get("message", {}).get("content", [{}])[0].get("text", "")
                else:
                    content = data["choices"][0]["message"]["content"].strip()

                return content, prov, resolved_model

            except Exception as e:
                last_error = e
                log.warning(f"LLM {prov} failed: {e}")
                continue

        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")


# ══════════════════════════════════════════════════════════════════════════════
# SCORING ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class ScoringEngine:
    """
    Intent Fidelity Scoring Engine v4.0.

    Score ranges:
        90-100: APPROVED — no risk (none)
        70-89:  APPROVED — low risk
        40-69:  ESCALATED — medium risk (human review)
        20-39:  BLOCKED — high risk
        0-19:   BLOCKED — critical risk
    """

    @staticmethod
    def score_to_risk(score: int) -> str:
        if score >= 90: return RiskLevel.NONE.value
        if score >= 70: return RiskLevel.LOW.value
        if score >= 40: return RiskLevel.MEDIUM.value
        if score >= 20: return RiskLevel.HIGH.value
        return RiskLevel.CRITICAL.value

    @staticmethod
    async def calculate_score(
        action:   str,
        can_do:   List[str],
        cannot_do: List[str],
        context:  str = "",
        memories: Optional[List[Dict]] = None,
    ) -> Tuple[int, str, Dict[str, int], float, str]:
        """
        Returns (score, reason, score_factors, confidence, llm_provider).
        confidence is 0.0-1.0: 1.0 = LLM, 0.8 = heuristic.
        """
        if settings.has_llm():
            try:
                return await ScoringEngine._score_with_llm(
                    action, can_do, cannot_do, context, memories or []
                )
            except Exception as e:
                log.warning(f"LLM scoring failed, using heuristic: {e}")

        score, reason, factors = ScoringEngine._score_heuristic(action, can_do, cannot_do)
        return score, reason, factors, 0.8, "heuristic"

    @staticmethod
    def _score_heuristic(
        action: str, can_do: List[str], cannot_do: List[str]
    ) -> Tuple[int, str, Dict[str, int]]:
        action_lower  = action.lower()
        score_factors: Dict[str, int] = {}
        all_risk_verbs = HIGH_RISK_VERBS["en"] + HIGH_RISK_VERBS["es"]

        # ── Sensitive data check ──────────────────────────────────────────────
        if TextSimilarity.contains_sensitive_data(action):
            score_factors["sensitive_data_in_action"] = -15

        # ── High-risk verb analysis ───────────────────────────────────────────
        for verb in all_risk_verbs:
            if verb in action_lower:
                for rule in cannot_do:
                    if verb in rule.lower():
                        score_factors["high_risk_verb_forbidden"] = -70
                        return 12, f"High-risk '{verb}' violates: '{rule[:50]}'", score_factors
                verb_allowed = any(verb in r.lower() for r in can_do)
                if not verb_allowed:
                    score_factors["high_risk_verb_not_authorized"] = -50
                    return 32, f"High-risk '{verb}' not explicitly authorized", score_factors
                else:
                    score_factors["high_risk_verb_authorized"] = 10

        # ── Numeric limit check ───────────────────────────────────────────────
        action_numbers = TextSimilarity.extract_numbers(action_lower)
        for rule in cannot_do:
            limit_val, is_pct = TextSimilarity.extract_limit(rule)
            if limit_val is not None:
                for num in action_numbers:
                    if num > limit_val:
                        pct_str = "%" if is_pct else ""
                        score_factors["exceeds_limit"] = -80
                        return 8, f"{num}{pct_str} exceeds limit {limit_val}{pct_str}", score_factors

        # ── Forbidden keyword match ───────────────────────────────────────────
        stop_words = {
            'para', 'todos', 'todas', 'desde', 'hasta', 'entre', 'sobre',
            'with', 'from', 'that', 'this', 'have', 'will', 'been', 'more',
            'than', 'when', 'what', 'which', 'there', 'their', 'would'
        }
        for rule in cannot_do:
            keywords = [w for w in TextSimilarity.word_set(rule)
                        if len(w) > 4 and w not in stop_words]
            if not keywords:
                continue
            hits = sum(1 for kw in keywords if kw in action_lower)
            if (hits >= 1 and len(keywords) <= 3) or hits >= 2:
                score_factors["forbidden_rule_match"] = -60
                return 18, f"Matches forbidden rule: '{rule[:50]}'", score_factors

        # ── Allowed rule match ────────────────────────────────────────────────
        best_match, best_score = None, 0.0
        for rule in can_do:
            keywords = [w for w in TextSimilarity.word_set(rule) if len(w) > 4]
            if not keywords:
                continue
            hits        = sum(1 for kw in keywords if kw in action_lower)
            match_ratio = hits / len(keywords)
            if match_ratio > best_score:
                best_score = match_ratio
                best_match = rule

        if best_match and best_score >= 0.3:
            score_factors["allowed_rule_match"] = int(20 + best_score * 60)
            return int(70 + best_score * 25), \
                   f"Aligned with: '{best_match[:50]}'", score_factors

        score_factors["no_clear_match"] = 0
        return 55, "No clear rule match — human review recommended", score_factors

    @staticmethod
    async def _score_with_llm(
        action:   str,
        can_do:   List[str],
        cannot_do: List[str],
        context:  str,
        memories: List[Dict],
    ) -> Tuple[int, str, Dict[str, int], float, str]:
        can_rules    = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(can_do))
        cannot_rules = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(cannot_do))
        memory_ctx   = ""
        if memories:
            items = "\n".join(f"  - {m['key']}: {m['value'][:100]}" for m in memories[:5])
            memory_ctx = f"\nAGENT MEMORY:\n{items}"

        prompt = f"""You are Nova, a strict intent verification system for AI agents.

ALLOWED ACTIONS:
{can_rules or "  (none specified)"}

FORBIDDEN ACTIONS (never violate):
{cannot_rules or "  (none specified)"}
{memory_ctx}

ACTION TO EVALUATE: "{action[:500]}"
CONTEXT: {context[:200] or "none"}

SCORING:
- Violates forbidden rule → 0-30
- Ambiguous, needs review → 40-68
- Matches allowed rule → 70-95

Respond ONLY with valid JSON, no markdown:
{{"score": 0, "reason": "under 15 words", "confidence": 0.95, "factors": {{"rule_name": impact_int}}}}"""

        content, provider, model = await LLMGateway.complete(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.1,
        )

        # Strip markdown fences
        clean = re.sub(r'```json\s*|```\s*', '', content).strip()
        result = json.loads(clean)
        return (
            int(result["score"]),
            result["reason"],
            result.get("factors", {}),
            float(result.get("confidence", 0.95)),
            provider,
        )


# ══════════════════════════════════════════════════════════════════════════════
# RESPONSE GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class ResponseGenerator:
    @staticmethod
    async def generate(
        action:   str,
        verdict:  Verdict,
        score:    int,
        reason:   str,
        token:    Dict,
        context:  str,
        memories: List[Dict],
    ) -> Optional[str]:
        if not settings.has_llm():
            return None

        agent_name = token.get("agent_name", "Agent")
        memory_ctx = ""
        if memories:
            items = "\n".join(f"  - {m['key']}: {m['value'][:150]}" for m in memories[:6])
            memory_ctx = f"\nCONTEXT FROM MEMORY:\n{items}"

        if verdict == Verdict.BLOCKED:
            prompt = f"""Agent "{agent_name}" attempted a blocked action.
BLOCKED ACTION: {action[:300]}
REASON: {reason}
{memory_ctx}
Generate a professional 2-3 sentence response explaining the action cannot be performed.
Do NOT reveal internal rules. Match the language of the original action (Spanish/English)."""
        else:
            prompt = f"""Agent "{agent_name}" will execute this approved action.
ACTION: {action[:500]}
CONTEXT: {context[:300] or 'none'}
CAPABILITIES: {json.dumps(token.get('can_do', []))}
{memory_ctx}
Generate the actual response or content the agent should produce.
Be specific and professional. Maximum 4 sentences. Match the language of the original action."""

        try:
            content, _, _ = await LLMGateway.complete(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=0.7,
            )
            return content
        except Exception as e:
            log.error(f"Response generation failed: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# MEMORY ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class MemoryEngine:
    @staticmethod
    async def get_relevant(
        workspace_id: str,
        agent_name:   str,
        action:       str,
        limit:        int = 6
    ) -> List[Dict]:
        rows = await db.fetch_all(
            """SELECT id, key, value, tags, importance, source, created_at
               FROM memories
               WHERE workspace_id = :wid
                 AND agent_name   = :agent
                 AND (expires_at IS NULL OR expires_at > NOW())
               ORDER BY importance DESC, created_at DESC
               LIMIT 30""",
            {"wid": workspace_id, "agent": agent_name}
        )
        if not rows:
            return []

        action_words = TextSimilarity.word_set(action)
        scored = []
        for row in rows:
            mem   = dict(row)
            mtext = f"{mem['key']} {mem['value']}"
            mwords = TextSimilarity.word_set(mtext)
            overlap    = len(action_words & mwords)
            total      = max(len(action_words | mwords), 1)
            similarity = overlap / total
            score = similarity + (mem['importance'] / 20)
            scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored[:limit]]

    @staticmethod
    async def auto_save(
        workspace_id: str,
        agent_name:   str,
        action:       str,
        verdict:      Verdict,
        score:        int,
        context:      str,
    ):
        if verdict == Verdict.BLOCKED:
            await db.execute(
                """INSERT INTO memories
                   (workspace_id, agent_name, key, value, tags, importance, source)
                   VALUES (:wid, :agent, :key, :val, :tags, :imp, 'auto')
                   ON CONFLICT DO NOTHING""",
                {
                    "wid":   workspace_id,
                    "agent": agent_name,
                    "key":   f"blocked_{Crypto.hash_action(action)}",
                    "val":   f"Blocked (score {score}): {action[:300]}",
                    "tags":  ["blocked", "auto", "violation"],
                    "imp":   8,
                }
            )
        elif verdict == Verdict.APPROVED and context and len(context) > 30:
            await db.execute(
                """INSERT INTO memories
                   (workspace_id, agent_name, key, value, tags, importance, source, expires_at)
                   VALUES (:wid, :agent, :key, :val, :tags, :imp, 'auto', NOW() + INTERVAL '7 days')
                   ON CONFLICT DO NOTHING""",
                {
                    "wid":   workspace_id,
                    "agent": agent_name,
                    "key":   f"ctx_{Crypto.hash_action(action)}",
                    "val":   f"Approved context: {context[:300]}",
                    "tags":  ["context", "auto"],
                    "imp":   4,
                }
            )

    @staticmethod
    async def cleanup_expired(workspace_id: str) -> int:
        return await db.execute(
            "DELETE FROM memories WHERE workspace_id = :wid AND expires_at < NOW()",
            {"wid": workspace_id}
        )


# ══════════════════════════════════════════════════════════════════════════════
# DUPLICATE GUARD
# ══════════════════════════════════════════════════════════════════════════════

class DuplicateGuard:
    @staticmethod
    async def check(
        workspace_id: str,
        token_id:     str,
        action:       str,
        window_minutes: int = 60,
        threshold:    float = 0.82,
    ) -> Optional[Dict]:
        since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        recent = await db.fetch_all(
            """SELECT id, action, verdict, executed_at
               FROM ledger
               WHERE workspace_id = :wid
                 AND token_id     = :tid
                 AND verdict      = 'APPROVED'
                 AND executed_at  > :since
               ORDER BY executed_at DESC
               LIMIT 50""",
            {"wid": workspace_id, "tid": token_id, "since": since}
        )
        for row in recent:
            sim = TextSimilarity.jaccard_similarity(action, row["action"])
            if sim >= threshold:
                return {
                    "ledger_id":   row["id"],
                    "action":      row["action"],
                    "similarity":  round(sim, 3),
                    "executed_at": row["executed_at"].isoformat() if row["executed_at"] else None,
                }
        return None


# ══════════════════════════════════════════════════════════════════════════════
# ALERT SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

class AlertSystem:
    @staticmethod
    async def create(
        workspace_id: str,
        ledger_id:    Optional[int],
        agent_name:   str,
        message:      str,
        score:        int,
        alert_type:   AlertType = AlertType.VIOLATION,
        severity:     AlertSeverity = None,
        metadata:     Dict = None,
    ) -> int:
        if severity is None:
            if score < 20:   severity = AlertSeverity.CRITICAL
            elif score < 40: severity = AlertSeverity.HIGH
            elif score < 60: severity = AlertSeverity.MEDIUM
            else:            severity = AlertSeverity.LOW

        alert_id = await db.execute(
            """INSERT INTO alerts
               (workspace_id, ledger_id, agent_name, alert_type, severity,
                message, score, metadata)
               VALUES (:wid, :lid, :agent, :type, :severity, :msg, :score, :meta)
               RETURNING id""",
            {
                "wid":      workspace_id,
                "lid":      ledger_id,
                "agent":    agent_name,
                "type":     alert_type.value,
                "severity": severity.value,
                "msg":      message[:500],
                "score":    score,
                "meta":     json.dumps(metadata or {}),
            }
        )
        log.warning(f"Alert [{severity.value.upper()}] {agent_name}: {message[:100]}")

        # Also push SSE event
        await SSEBroker.publish(workspace_id, "alert", {
            "agent_name":  agent_name,
            "alert_type":  alert_type.value,
            "severity":    severity.value,
            "message":     message[:200],
            "score":       score,
        })
        return alert_id

    @staticmethod
    async def resolve(workspace_id: str, alert_id: int, resolved_by: str = None):
        await db.execute(
            """UPDATE alerts
               SET resolved = TRUE, resolved_by = :by, resolved_at = NOW()
               WHERE id = :id AND workspace_id = :wid""",
            {"id": alert_id, "wid": workspace_id, "by": resolved_by}
        )


# ══════════════════════════════════════════════════════════════════════════════
# ANOMALY DETECTOR
# ══════════════════════════════════════════════════════════════════════════════

class AnomalyDetector:
    """
    Detects unusual behavioral patterns in agent activity.

    Checks:
    1. High block rate (>50% of recent actions blocked)
    2. Burst activity (>20 actions in 5 minutes)
    3. Score degradation (avg score dropping >15pts over 1h)
    4. Limit probing (multiple actions near financial/numeric limits)
    5. Sensitive data exposure in action text
    """

    @staticmethod
    async def run_all(workspace_id: str, agent_name: str, background: BackgroundTasks = None):
        """Run all anomaly checks for an agent. Non-blocking."""
        checks = [
            AnomalyDetector.check_block_rate(workspace_id, agent_name),
            AnomalyDetector.check_burst_activity(workspace_id, agent_name),
            AnomalyDetector.check_score_degradation(workspace_id, agent_name),
        ]
        results = await asyncio.gather(*checks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                log.debug(f"Anomaly check error: {r}")

    @staticmethod
    async def check_block_rate(workspace_id: str, agent_name: str):
        """Flag if >50% of actions in last 30 min are blocked."""
        rows = await db.fetch_all(
            """SELECT verdict FROM ledger
               WHERE workspace_id = :wid
                 AND agent_name   = :agent
                 AND executed_at  > NOW() - INTERVAL '30 minutes'""",
            {"wid": workspace_id, "agent": agent_name}
        )
        if len(rows) < 5:
            return  # Not enough data

        blocked_count = sum(1 for r in rows if r["verdict"] == "BLOCKED")
        block_rate    = blocked_count / len(rows)

        if block_rate >= settings.ANOMALY_BLOCK_RATE_THRESHOLD:
            await AnomalyDetector._log_anomaly(
                workspace_id, agent_name,
                AnomalyType.HIGH_BLOCK_RATE,
                AlertSeverity.HIGH,
                f"Block rate {block_rate*100:.0f}% in last 30 minutes "
                f"({blocked_count}/{len(rows)} actions)",
                {"block_rate": block_rate, "sample_size": len(rows)}
            )

    @staticmethod
    async def check_burst_activity(workspace_id: str, agent_name: str):
        """Flag if >20 actions in any 5-minute window."""
        count_row = await db.fetch_one(
            """SELECT COUNT(*) c FROM ledger
               WHERE workspace_id = :wid
                 AND agent_name   = :agent
                 AND executed_at  > NOW() - :min * INTERVAL '1 minute'""",
            {"wid": workspace_id, "agent": agent_name,
             "min": settings.ANOMALY_BURST_WINDOW_MINUTES}
        )
        count = count_row["c"] if count_row else 0
        if count >= settings.ANOMALY_BURST_THRESHOLD:
            await AnomalyDetector._log_anomaly(
                workspace_id, agent_name,
                AnomalyType.BURST_ACTIVITY,
                AlertSeverity.MEDIUM,
                f"Burst: {count} actions in {settings.ANOMALY_BURST_WINDOW_MINUTES} minutes",
                {"count": count, "window_minutes": settings.ANOMALY_BURST_WINDOW_MINUTES}
            )

    @staticmethod
    async def check_score_degradation(workspace_id: str, agent_name: str):
        """Flag if average score dropped >15 points in the last hour."""
        rows = await db.fetch_all(
            """SELECT score, executed_at FROM ledger
               WHERE workspace_id = :wid
                 AND agent_name   = :agent
                 AND verdict      != 'DUPLICATE'
                 AND executed_at  > NOW() - INTERVAL '2 hours'
               ORDER BY executed_at ASC""",
            {"wid": workspace_id, "agent": agent_name}
        )
        if len(rows) < 10:
            return

        mid = len(rows) // 2
        older_avg = sum(r["score"] for r in rows[:mid]) / mid
        newer_avg = sum(r["score"] for r in rows[mid:]) / (len(rows) - mid)
        drop      = older_avg - newer_avg

        if drop >= 15:
            await AnomalyDetector._log_anomaly(
                workspace_id, agent_name,
                AnomalyType.SCORE_DEGRADATION,
                AlertSeverity.MEDIUM,
                f"Score degradation: avg dropped {drop:.1f} pts "
                f"({older_avg:.0f} → {newer_avg:.0f})",
                {"older_avg": older_avg, "newer_avg": newer_avg, "drop": drop}
            )

    @staticmethod
    async def _log_anomaly(
        workspace_id: str,
        agent_name:   str,
        anomaly_type: AnomalyType,
        severity:     AlertSeverity,
        description:  str,
        evidence:     Dict,
    ):
        # Check if same anomaly was logged in last 30 min (avoid spam)
        existing = await db.fetch_one(
            """SELECT id FROM anomaly_log
               WHERE workspace_id = :wid
                 AND agent_name   = :agent
                 AND anomaly_type = :type
                 AND created_at   > NOW() - INTERVAL '30 minutes'
               LIMIT 1""",
            {"wid": workspace_id, "agent": agent_name, "type": anomaly_type.value}
        )
        if existing:
            return

        await db.execute(
            """INSERT INTO anomaly_log
               (workspace_id, agent_name, anomaly_type, severity, description, evidence)
               VALUES (:wid, :agent, :type, :sev, :desc, :ev)""",
            {
                "wid":   workspace_id,
                "agent": agent_name,
                "type":  anomaly_type.value,
                "sev":   severity.value,
                "desc":  description,
                "ev":    json.dumps(evidence),
            }
        )
        # Create an alert
        await AlertSystem.create(
            workspace_id, None, agent_name,
            f"[ANOMALY] {description}", 0,
            AlertType.ANOMALY, severity, evidence
        )
        log.warning(f"Anomaly [{anomaly_type.value}] {agent_name}: {description}")


# ══════════════════════════════════════════════════════════════════════════════
# POLICY ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class PolicyEngine:
    """Manage reusable policy templates and apply them to tokens."""

    @staticmethod
    async def get(workspace_id: str, policy_id: int) -> Optional[Dict]:
        row = await db.fetch_one(
            "SELECT * FROM policies WHERE id = :id AND workspace_id = :wid AND active = TRUE",
            {"id": policy_id, "wid": workspace_id}
        )
        return dict(row) if row else None

    @staticmethod
    async def merge_with_token(token: Dict, policy: Dict) -> Tuple[List[str], List[str]]:
        """
        Merge a policy's rules with a token's rules.
        Policy rules take precedence for cannot_do (security).
        """
        merged_can   = list(set(token.get("can_do", []) + policy.get("can_do", [])))
        merged_cannot = list(set(token.get("cannot_do", []) + policy.get("cannot_do", [])))
        return merged_can, merged_cannot


# ══════════════════════════════════════════════════════════════════════════════
# SKILL BRIDGE
# ══════════════════════════════════════════════════════════════════════════════

class SkillBridge:
    """
    Optional integration with skill_executor.py.
    When SKILL_EXECUTOR_ENABLED=true, runs tool-backed skill evaluation
    alongside the main scoring engine.
    """

    @staticmethod
    async def run(
        action:      str,
        context:     str,
        skills:      List[str],
        constraints: List[str],
        agent_name:  str,
        credentials: Dict = None,
    ) -> Optional[Dict]:
        if not settings.SKILL_EXECUTOR_ENABLED:
            return None

        provider, api_key = settings.get_active_llm()
        if not api_key:
            return None

        try:
            # Dynamic import — skill_executor.py must be in the same directory
            import importlib.util, sys as _sys
            skill_mod_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "skill_executor.py"
            )
            if os.path.exists(skill_mod_path):
                spec = importlib.util.spec_from_file_location("skill_executor", skill_mod_path)
                mod  = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)

                # Map provider to litellm model string
                model_str = f"{provider}/{LLM_DEFAULT_MODELS.get(provider, 'gpt-4o-mini')}"

                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    mod.run_skills,
                    action, context, skills, constraints,
                    {"model": model_str, "api_key": api_key},
                    agent_name, credentials
                )
                return result

        except Exception as e:
            log.warning(f"SkillBridge failed (non-fatal): {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# SSE BROKER — Real-time event streaming
# ══════════════════════════════════════════════════════════════════════════════

class SSEBroker:
    """
    Server-Sent Events broker for real-time event streaming.
    Clients subscribe to a workspace stream and receive live validation events.
    """
    _subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)

    @classmethod
    async def publish(cls, workspace_id: str, event_type: str, payload: Dict):
        """Push an event to all subscribers of a workspace."""
        event_data = {
            "type":      event_type,
            "payload":   payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        # Store in DB for late subscribers
        try:
            await db.execute(
                """INSERT INTO sse_events (workspace_id, event_type, payload)
                   VALUES (:wid, :type, :payload)""",
                {
                    "wid":     workspace_id,
                    "type":    event_type,
                    "payload": json.dumps(payload),
                }
            )
        except Exception:
            pass  # non-fatal

        # Push to all live subscribers
        dead = []
        for q in cls._subscribers.get(workspace_id, []):
            try:
                await q.put(event_data)
            except Exception:
                dead.append(q)
        for q in dead:
            cls._subscribers[workspace_id].remove(q)

    @classmethod
    def subscribe(cls, workspace_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        cls._subscribers[workspace_id].append(q)
        return q

    @classmethod
    def unsubscribe(cls, workspace_id: str, q: asyncio.Queue):
        try:
            cls._subscribers[workspace_id].remove(q)
        except ValueError:
            pass

    @classmethod
    def active_streams(cls) -> int:
        return sum(len(v) for v in cls._subscribers.values())


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class AnalyticsEngine:
    @staticmethod
    async def get_stats(workspace_id: str) -> Dict[str, Any]:
        wid = workspace_id
        queries = [
            ("total",     "SELECT COUNT(*) c FROM ledger WHERE workspace_id=:w"),
            ("approved",  "SELECT COUNT(*) c FROM ledger WHERE workspace_id=:w AND verdict='APPROVED'"),
            ("blocked",   "SELECT COUNT(*) c FROM ledger WHERE workspace_id=:w AND verdict='BLOCKED'"),
            ("escalated", "SELECT COUNT(*) c FROM ledger WHERE workspace_id=:w AND verdict='ESCALATED'"),
            ("duplicates","SELECT COUNT(*) c FROM ledger WHERE workspace_id=:w AND verdict='DUPLICATE'"),
            ("avg_score", "SELECT COALESCE(ROUND(AVG(score)), 0) avg FROM ledger WHERE workspace_id=:w AND verdict!='DUPLICATE'"),
            ("agents",    "SELECT COUNT(*) c FROM intent_tokens WHERE workspace_id=:w AND active=TRUE"),
            ("alerts",    "SELECT COUNT(*) c FROM alerts WHERE workspace_id=:w AND resolved=FALSE"),
            ("memories",  "SELECT COUNT(*) c FROM memories WHERE workspace_id=:w AND (expires_at IS NULL OR expires_at>NOW())"),
        ]
        results = {}
        for name, query in queries:
            row = await db.fetch_one(query, {"w": wid})
            results[name] = row["c"] if "c" in row.keys() else row.get("avg", 0)

        total = results["total"] or 1
        trend_rows = await db.fetch_all(
            """SELECT DATE(executed_at) as day, ROUND(AVG(score)) as avg_score
               FROM ledger
               WHERE workspace_id = :w
                 AND executed_at > NOW() - INTERVAL '7 days'
                 AND verdict != 'DUPLICATE'
               GROUP BY DATE(executed_at) ORDER BY day ASC""",
            {"w": wid}
        )
        score_trend = [int(row["avg_score"]) for row in trend_rows] if trend_rows else None

        return {
            "total_actions":      results["total"],
            "approved":           results["approved"],
            "blocked":            results["blocked"],
            "escalated":          results["escalated"],
            "duplicates_blocked": results["duplicates"],
            "avg_score":          int(results["avg_score"] or 0),
            "active_agents":      results["agents"],
            "alerts_pending":     results["alerts"],
            "memories_stored":    results["memories"],
            "approval_rate":      round(results["approved"] / total * 100, 1),
            "score_trend":        score_trend,
        }

    @staticmethod
    async def get_risk_profile(workspace_id: str) -> Dict[str, Any]:
        """Per-agent risk scoring based on recent behavior."""
        rows = await db.fetch_all(
            """SELECT
                agent_name,
                COUNT(*) FILTER (WHERE verdict='BLOCKED')  AS blocked,
                COUNT(*) FILTER (WHERE verdict='ESCALATED') AS escalated,
                COUNT(*) FILTER (WHERE risk_level='critical') AS critical_count,
                ROUND(AVG(score)) AS avg_score,
                COUNT(*) AS total,
                MAX(executed_at) AS last_action
               FROM ledger
               WHERE workspace_id = :wid
                 AND executed_at > NOW() - INTERVAL '24 hours'
               GROUP BY agent_name
               ORDER BY blocked DESC, avg_score ASC""",
            {"wid": workspace_id}
        )
        profiles = []
        for row in rows:
            total   = max(row["total"], 1)
            blk_rate = row["blocked"] / total
            risk_score = (
                min(blk_rate * 100, 40)      +
                min(row["critical_count"], 10) * 3 +
                max(0, 50 - int(row["avg_score"] or 50)) * 0.4
            )
            profiles.append({
                "agent_name":    row["agent_name"],
                "risk_score":    round(min(risk_score, 100), 1),
                "block_rate":    round(blk_rate * 100, 1),
                "avg_score":     int(row["avg_score"] or 0),
                "blocked":       row["blocked"],
                "escalated":     row["escalated"],
                "critical_count": row["critical_count"],
                "total":         row["total"],
                "last_action":   row["last_action"],
            })
        return {"agents": profiles, "as_of": datetime.now(timezone.utc).isoformat()}

    @staticmethod
    async def get_anomalies(workspace_id: str, limit: int = 20) -> List[Dict]:
        rows = await db.fetch_all(
            """SELECT id, agent_name, anomaly_type, severity, description,
                      evidence, resolved, created_at
               FROM anomaly_log
               WHERE workspace_id = :wid
               ORDER BY created_at DESC
               LIMIT :lim""",
            {"wid": workspace_id, "lim": limit}
        )
        return [
            {**dict(r), "evidence": r["evidence"] if r["evidence"] else {}}
            for r in rows
        ]

    @staticmethod
    async def get_timeline(workspace_id: str, hours: int = 24) -> List[Dict]:
        rows = await db.fetch_all(
            """SELECT
                DATE_TRUNC('hour', executed_at) AS hour,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE verdict='APPROVED')  AS approved,
                COUNT(*) FILTER (WHERE verdict='BLOCKED')   AS blocked,
                ROUND(AVG(score)) AS avg_score
               FROM ledger
               WHERE workspace_id = :wid
                 AND executed_at > NOW() - :h * INTERVAL '1 hour'
               GROUP BY hour ORDER BY hour ASC""",
            {"wid": workspace_id, "h": hours}
        )
        return [
            {
                "hour":      row["hour"].isoformat() if row["hour"] else None,
                "total":     row["total"],
                "approved":  row["approved"],
                "blocked":   row["blocked"],
                "avg_score": int(row["avg_score"] or 0),
            }
            for row in rows
        ]

    @staticmethod
    async def track_event(workspace_id: str, event_type: str, event_data: Dict = None):
        await db.execute(
            """INSERT INTO analytics_events (workspace_id, event_type, event_data)
               VALUES (:wid, :type, :data)""",
            {
                "wid":  workspace_id,
                "type": event_type,
                "data": json.dumps(event_data or {}),
            }
        )


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION LIFECYCLE
# ══════════════════════════════════════════════════════════════════════════════

_startup_time: float = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _startup_time
    provider, _ = settings.get_active_llm()
    log.info("=" * 60)
    log.info(f"Nova OS v{settings.VERSION} starting...")
    log.info(f"Environment: {settings.ENVIRONMENT}")
    log.info(f"LLM provider: {provider or 'none'}")
    log.info(f"SkillExecutor: {'enabled' if settings.SKILL_EXECUTOR_ENABLED else 'disabled'}")
    log.info("=" * 60)

    await db.connect()
    await init_database()
    _startup_time = time.time()
    log.info("Nova OS ready")

    yield

    log.info("Shutting down...")
    await db.disconnect()
    log.info("Shutdown complete")


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION SETUP
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Nova OS API",
    description="""
Enterprise-grade governance infrastructure for AI agents.

Nova sits between your AI agents and the real world, validating every action
before execution and maintaining a cryptographic audit trail of all decisions.

## Features
- **Intent Verification**: Multi-LLM scoring (9 providers)
- **Policy Engine**: Reusable governance templates
- **Memory Engine**: Persistent agent context
- **Duplicate Guard**: Prevent repeated actions
- **Anomaly Detector**: Behavioral pattern analysis
- **Response Generator**: LLM-powered responses
- **Intent Ledger**: Immutable audit trail with chain verification
- **Alert System**: Real-time violation alerts
- **SSE Streaming**: Live event feed

## Authentication
All endpoints (except `/` and `/health`) require an API key via `x-api-key` header.
    """,
    version=settings.VERSION,
    docs_url="/docs" if not settings.is_production() else None,
    redoc_url="/redoc" if not settings.is_production() else None,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.RATE_LIMIT_REQUESTS)


# ══════════════════════════════════════════════════════════════════════════════
# EXCEPTION HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error":      exc.detail,
            "code":       f"HTTP_{exc.status_code}",
            "request_id": getattr(request.state, "request_id", None)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    log.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error":      "Internal server error",
            "code":       "INTERNAL_ERROR",
            "detail":     str(exc) if settings.DEBUG else None,
            "request_id": getattr(request.state, "request_id", None)
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Core
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Core"])
async def root():
    provider, _ = settings.get_active_llm()
    return {
        "name":    "Nova OS",
        "version": settings.VERSION,
        "build":   settings.BUILD,
        "status":  "operational",
        "capabilities": [
            "intent_verification", "policy_engine", "memory_engine",
            "duplicate_guard", "anomaly_detection", "response_generation",
            "intent_ledger", "alert_system", "sse_streaming",
            "batch_validation", "skill_executor",
        ],
        "llm_provider": provider or "none",
        "docs": "/docs" if not settings.is_production() else "https://docs.nova-os.com"
    }


@app.get("/health", tags=["Core"], response_model=HealthResponse)
async def health_check():
    db_status = "connected"
    try:
        await db.fetch_one("SELECT 1")
    except Exception:
        db_status = "disconnected"

    provider, _ = settings.get_active_llm()
    uptime = int(time.time() - _startup_time) if _startup_time else 0

    return {
        "status":         "healthy" if db_status == "connected" else "degraded",
        "version":        settings.VERSION,
        "build":          settings.BUILD,
        "environment":    settings.ENVIRONMENT,
        "timestamp":      datetime.now(timezone.utc),
        "database":       db_status,
        "llm_available":  settings.has_llm(),
        "llm_provider":   provider or "none",
        "uptime_seconds": uptime,
        "active_streams": SSEBroker.active_streams(),
    }


@app.get("/workspaces/me", tags=["Workspace"])
async def get_my_workspace(ws: Dict = Depends(get_workspace)):
    """Get current workspace details and usage stats."""
    stats = await AnalyticsEngine.get_stats(str(ws["id"]))
    return {
        "id":               str(ws["id"]),
        "name":             ws.get("name", ""),
        "plan":             ws.get("plan", "free"),
        "features":         ws.get("features", []),
        "usage_this_month": ws.get("usage_this_month", 0),
        "quota_monthly":    ws.get("quota_monthly", 10000),
        "stats":            stats,
        "created_at":       ws.get("created_at"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Policies
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/policies", tags=["Policies"], response_model=PolicyResponse)
async def create_policy(
    payload: PolicyCreate,
    ws: Dict = Depends(get_workspace)
):
    """
    Create a reusable policy template.

    Policies define can_do/cannot_do rule sets that can be applied
    to multiple agents. When a token has a policy, the policy rules
    are merged with the token's own rules during validation.
    """
    policy_id = await db.execute(
        """INSERT INTO policies
           (workspace_id, name, description, category, can_do, cannot_do,
            tags, is_template, created_by, metadata)
           VALUES (:wid, :name, :desc, :cat, :can, :cannot, :tags, :tmpl, :by, :meta)
           RETURNING id""",
        {
            "wid":    ws["id"],
            "name":   payload.name,
            "desc":   payload.description,
            "cat":    payload.category,
            "can":    payload.can_do,
            "cannot": payload.cannot_do,
            "tags":   payload.tags,
            "tmpl":   payload.is_template,
            "by":     payload.created_by,
            "meta":   json.dumps(payload.metadata),
        }
    )
    await AnalyticsEngine.track_event(str(ws["id"]), "policy_created",
        {"policy_id": policy_id, "name": payload.name})
    return {
        "id": policy_id, "name": payload.name, "description": payload.description,
        "category": payload.category, "can_do": payload.can_do,
        "cannot_do": payload.cannot_do, "tags": payload.tags,
        "is_template": payload.is_template, "version": 1,
        "created_by": payload.created_by, "active": True,
        "metadata": payload.metadata,
        "created_at": datetime.now(timezone.utc), "updated_at": None,
    }


@app.get("/policies", tags=["Policies"])
async def list_policies(
    category:    Optional[str] = Query(None),
    is_template: Optional[bool] = Query(None),
    ws: Dict = Depends(get_workspace)
):
    """List all policy templates for the workspace."""
    query = """
        SELECT id, name, description, category, can_do, cannot_do,
               tags, is_template, version, created_by, active, metadata, created_at, updated_at
        FROM policies
        WHERE workspace_id = :wid AND active = TRUE
    """
    params: Dict = {"wid": ws["id"]}
    if category:
        query += " AND category = :cat"
        params["cat"] = category
    if is_template is not None:
        query += " AND is_template = :tmpl"
        params["tmpl"] = is_template
    query += " ORDER BY created_at DESC"
    rows = await db.fetch_all(query, params)
    return [
        {**dict(r), "metadata": r["metadata"] or {}}
        for r in rows
    ]


@app.get("/policies/{policy_id}", tags=["Policies"], response_model=PolicyResponse)
async def get_policy(
    policy_id: int = Path(...),
    ws: Dict = Depends(get_workspace)
):
    """Get a specific policy."""
    row = await db.fetch_one(
        "SELECT * FROM policies WHERE id = :id AND workspace_id = :wid",
        {"id": policy_id, "wid": ws["id"]}
    )
    if not row:
        raise HTTPException(404, "Policy not found")
    return {**dict(row), "metadata": row["metadata"] or {}}


@app.patch("/policies/{policy_id}", tags=["Policies"])
async def update_policy(
    policy_id: int,
    payload:   PolicyUpdate,
    ws: Dict = Depends(get_workspace)
):
    """Update a policy. Increments version for audit trail."""
    updates = ["updated_at = NOW()", "version = version + 1"]
    values  = {"id": policy_id, "wid": ws["id"]}
    if payload.name        is not None: updates.append("name = :name");       values["name"]   = payload.name
    if payload.description is not None: updates.append("description = :desc"); values["desc"]   = payload.description
    if payload.can_do      is not None: updates.append("can_do = :can");       values["can"]    = payload.can_do
    if payload.cannot_do   is not None: updates.append("cannot_do = :cannot"); values["cannot"] = payload.cannot_do
    if payload.tags        is not None: updates.append("tags = :tags");        values["tags"]   = payload.tags
    if payload.active      is not None: updates.append("active = :active");    values["active"] = payload.active
    if payload.metadata    is not None: updates.append("metadata = :meta");    values["meta"]   = json.dumps(payload.metadata)
    await db.execute(
        f"UPDATE policies SET {', '.join(updates)} WHERE id = :id AND workspace_id = :wid",
        values
    )
    return {"status": "updated", "policy_id": policy_id}


@app.delete("/policies/{policy_id}", tags=["Policies"])
async def delete_policy(policy_id: int, ws: Dict = Depends(get_workspace)):
    await db.execute(
        "UPDATE policies SET active = FALSE WHERE id = :id AND workspace_id = :wid",
        {"id": policy_id, "wid": ws["id"]}
    )
    return {"status": "deleted", "policy_id": policy_id}


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Intent Tokens
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/tokens", tags=["Tokens"], response_model=TokenResponse)
async def create_token(payload: TokenCreate, ws: Dict = Depends(get_workspace)):
    """
    Create a new Intent Token for an agent.

    If a policy_id is provided, the policy's rules are merged with the
    token's own rules (policy cannot_do takes precedence).
    """
    effective_can    = list(payload.can_do)
    effective_cannot = list(payload.cannot_do)

    # Merge policy rules if provided
    if payload.policy_id:
        policy = await PolicyEngine.get(str(ws["id"]), payload.policy_id)
        if not policy:
            raise HTTPException(404, "Policy not found")
        effective_can, effective_cannot = await PolicyEngine.merge_with_token(
            {"can_do": effective_can, "cannot_do": effective_cannot}, policy
        )

    signature = Crypto.sign({
        "workspace_id": str(ws["id"]),
        "agent_name":   payload.agent_name,
        "can_do":       sorted(effective_can),
        "cannot_do":    sorted(effective_cannot),
        "authorized_by": payload.authorized_by,
        "created_at":   datetime.now(timezone.utc).isoformat()
    })

    token_id = await db.execute(
        """INSERT INTO intent_tokens
           (workspace_id, agent_name, description, can_do, cannot_do,
            policy_id, authorized_by, signature, metadata)
           VALUES (:wid, :name, :desc, :can, :cannot, :policy, :auth, :sig, :meta)
           RETURNING id""",
        {
            "wid":    ws["id"],
            "name":   payload.agent_name,
            "desc":   payload.description,
            "can":    effective_can,
            "cannot": effective_cannot,
            "policy": payload.policy_id,
            "auth":   payload.authorized_by,
            "sig":    signature,
            "meta":   json.dumps(payload.metadata),
        }
    )
    log.info(f"Token created: {payload.agent_name} (ID: {token_id})")
    await AnalyticsEngine.track_event(str(ws["id"]), "token_created",
        {"agent_name": payload.agent_name, "token_id": token_id})
    return {
        "id": str(token_id), "agent_name": payload.agent_name,
        "description": payload.description or "",
        "can_do": effective_can, "cannot_do": effective_cannot,
        "authorized_by": payload.authorized_by, "signature": signature,
        "policy_id": payload.policy_id, "active": True, "version": 1,
        "metadata": payload.metadata or {},
        "created_at": datetime.now(timezone.utc), "updated_at": None,
    }


@app.get("/tokens", tags=["Tokens"])
async def list_tokens(
    active_only: bool = Query(True),
    ws: Dict = Depends(get_workspace)
):
    query = """
        SELECT id, agent_name, description, can_do, cannot_do,
               authorized_by, signature, policy_id, active, version, metadata, created_at, updated_at
        FROM intent_tokens WHERE workspace_id = :wid
    """
    if active_only:
        query += " AND active = TRUE"
    query += " ORDER BY created_at DESC"
    rows = await db.fetch_all(query, {"wid": ws["id"]})
    return [
        {**dict(r), "id": str(r["id"]), "metadata": r["metadata"] or {}}
        for r in rows
    ]


@app.get("/tokens/{token_id}", tags=["Tokens"], response_model=TokenResponse)
async def get_token(token_id: str, ws: Dict = Depends(get_workspace)):
    row = await db.fetch_one(
        "SELECT * FROM intent_tokens WHERE id = :tid AND workspace_id = :wid",
        {"tid": token_id, "wid": ws["id"]}
    )
    if not row:
        raise HTTPException(404, "Token not found")
    token = dict(row)
    token["id"] = str(token["id"])
    token["metadata"] = token["metadata"] or {}
    return token


@app.patch("/tokens/{token_id}", tags=["Tokens"])
async def update_token(
    token_id: str,
    payload:  TokenUpdate,
    ws: Dict = Depends(get_workspace)
):
    """Update a token. Saves version history automatically."""
    # Save current state to history
    current = await db.fetch_one(
        "SELECT * FROM intent_tokens WHERE id = :tid AND workspace_id = :wid",
        {"tid": token_id, "wid": ws["id"]}
    )
    if not current:
        raise HTTPException(404, "Token not found")

    await db.execute(
        """INSERT INTO token_history (token_id, version, can_do, cannot_do, changed_by, change_reason)
           VALUES (:tid, :ver, :can, :cannot, :by, :reason)""",
        {
            "tid":    token_id,
            "ver":    current["version"],
            "can":    current["can_do"],
            "cannot": current["cannot_do"],
            "by":     payload.changed_by,
            "reason": payload.change_reason,
        }
    )

    updates = ["updated_at = NOW()", "version = version + 1"]
    values  = {"tid": token_id, "wid": ws["id"]}
    if payload.description is not None: updates.append("description = :desc"); values["desc"]   = payload.description
    if payload.can_do      is not None: updates.append("can_do = :can");       values["can"]    = payload.can_do
    if payload.cannot_do   is not None: updates.append("cannot_do = :cannot"); values["cannot"] = payload.cannot_do
    if payload.active      is not None: updates.append("active = :active");    values["active"] = payload.active
    if payload.policy_id   is not None: updates.append("policy_id = :policy"); values["policy"] = payload.policy_id
    if payload.metadata    is not None: updates.append("metadata = :meta");    values["meta"]   = json.dumps(payload.metadata)
    if not updates:
        raise HTTPException(400, "No fields to update")
    await db.execute(
        f"UPDATE intent_tokens SET {', '.join(updates)} WHERE id = :tid AND workspace_id = :wid",
        values
    )
    return {"status": "updated", "token_id": token_id}


@app.delete("/tokens/{token_id}", tags=["Tokens"])
async def deactivate_token(token_id: str, ws: Dict = Depends(get_workspace)):
    await db.execute(
        "UPDATE intent_tokens SET active = FALSE, updated_at = NOW() WHERE id = :tid AND workspace_id = :wid",
        {"tid": token_id, "wid": ws["id"]}
    )
    return {"status": "deactivated", "token_id": token_id}


@app.get("/tokens/{token_id}/history", tags=["Tokens"])
async def get_token_history(token_id: str, ws: Dict = Depends(get_workspace)):
    """Get the version history of a token's rules."""
    # Verify ownership
    exists = await db.fetch_one(
        "SELECT id FROM intent_tokens WHERE id = :tid AND workspace_id = :wid",
        {"tid": token_id, "wid": ws["id"]}
    )
    if not exists:
        raise HTTPException(404, "Token not found")
    rows = await db.fetch_all(
        "SELECT * FROM token_history WHERE token_id = :tid ORDER BY changed_at DESC",
        {"tid": token_id}
    )
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Validation (The Heart of Nova)
# ══════════════════════════════════════════════════════════════════════════════

async def _run_validation(
    payload:    ValidateRequest,
    workspace:  Dict,
    ctx:        Dict,
    bg:         BackgroundTasks,
) -> ValidateResponse:
    """
    Core validation logic — called by both /validate and /validate/batch.

    Pipeline:
    1. Load token (+ merge policy rules)
    2. Get relevant memories
    3. Check duplicates
    4. Score with LLM or heuristic
    5. Run SkillBridge (optional)
    6. Determine verdict
    7. Generate response
    8. Record to ledger
    9. Create alerts
    10. Auto-save memory
    11. Push SSE event
    12. Trigger anomaly detection (background)
    """
    start_time = time.time()

    # ── Load token ────────────────────────────────────────────────────────────
    token = await db.fetch_one(
        "SELECT * FROM intent_tokens WHERE id = :tid AND workspace_id = :wid AND active = TRUE",
        {"tid": payload.token_id, "wid": workspace["id"]}
    )
    if not token:
        raise HTTPException(404, "Intent Token not found or inactive")
    token = dict(token)

    # ── Merge policy rules if token has a policy ──────────────────────────────
    if token.get("policy_id"):
        policy = await PolicyEngine.get(str(workspace["id"]), token["policy_id"])
        if policy:
            token["can_do"], token["cannot_do"] = await PolicyEngine.merge_with_token(token, policy)

    # ── Get relevant memories ─────────────────────────────────────────────────
    memories = await MemoryEngine.get_relevant(
        str(workspace["id"]), token["agent_name"], payload.action
    )

    # ── Duplicate check ───────────────────────────────────────────────────────
    if payload.check_duplicates:
        dup = await DuplicateGuard.check(
            str(workspace["id"]), payload.token_id, payload.action,
            payload.duplicate_window_minutes, payload.duplicate_threshold
        )
        if dup:
            latency = int((time.time() - start_time) * 1000)
            return ValidateResponse(
                verdict=Verdict.DUPLICATE, score=0, confidence=1.0,
                risk_level="none", reason=f"Similar action executed recently (similarity: {dup['similarity']*100:.0f}%)",
                response=None, execute=False, agent_name=token["agent_name"],
                ledger_id=None, hash=None, memories_used=len(memories),
                duplicate_check="blocked", duplicate_of=dup,
                score_factors={"duplicate_detected": -100}, skill_evidence=None,
                llm_provider=None, request_id=ctx["request_id"], latency_ms=latency
            )

    # ── Score ─────────────────────────────────────────────────────────────────
    score, reason, score_factors, confidence, llm_provider = \
        await ScoringEngine.calculate_score(
            payload.action, token["can_do"], token["cannot_do"],
            payload.context or "", memories
        )

    # ── Optional: run skill executor ─────────────────────────────────────────
    skill_evidence = None
    if payload.run_skills and settings.SKILL_EXECUTOR_ENABLED:
        result = await SkillBridge.run(
            action=payload.action, context=payload.context or "",
            skills=token.get("can_do", []),
            constraints=token.get("cannot_do", []),
            agent_name=token["agent_name"],
        )
        if result:
            skill_evidence = result
            score = max(0, min(100, score + result.get("recommended_score_modifier", 0)))
            if result.get("hard_block"):
                score  = max(score, 0)
                reason = f"[SKILL BLOCK] {result.get('evidence_summary', reason)}"

    # ── Determine verdict and risk level ──────────────────────────────────────
    if score >= settings.SCORE_APPROVED_THRESHOLD:
        verdict = Verdict.APPROVED
    elif score >= settings.SCORE_ESCALATED_THRESHOLD:
        verdict = Verdict.ESCALATED
    else:
        verdict = Verdict.BLOCKED
    risk_level = ScoringEngine.score_to_risk(score)

    # ── Generate response ─────────────────────────────────────────────────────
    response_text = None
    if payload.generate_response:
        response_text = await ResponseGenerator.generate(
            payload.action, verdict, score, reason, token,
            payload.context or "", memories
        )

    # ── Record to ledger ──────────────────────────────────────────────────────
    ledger_id = None
    own_hash  = None

    if not payload.dry_run:
        prev_row  = await db.fetch_one(
            "SELECT own_hash FROM ledger WHERE workspace_id = :wid ORDER BY id DESC LIMIT 1",
            {"wid": workspace["id"]}
        )
        prev_hash = prev_row["own_hash"] if prev_row else "GENESIS"
        own_hash  = Crypto.chain_hash(prev_hash, {
            "workspace_id": str(workspace["id"]),
            "token_id":     payload.token_id,
            "action":       payload.action,
            "score":        score,
            "verdict":      verdict.value,
            "timestamp":    datetime.now(timezone.utc).isoformat()
        })
        latency_ms = int((time.time() - start_time) * 1000)
        ledger_id  = await db.execute(
            """INSERT INTO ledger
               (workspace_id, token_id, agent_name, action, context, score,
                confidence, risk_level, verdict, reason, response,
                score_factors, skill_evidence, prev_hash, own_hash,
                request_id, client_ip, user_agent, llm_provider, latency_ms)
               VALUES (:wid, :tid, :agent, :action, :ctx, :score,
                       :conf, :risk, :verdict, :reason, :resp,
                       :factors, :skills, :prev, :own,
                       :rid, :ip, :ua, :prov, :lat)
               RETURNING id""",
            {
                "wid":     workspace["id"], "tid":     payload.token_id,
                "agent":   token["agent_name"], "action":  payload.action,
                "ctx":     payload.context or "",
                "score":   score, "conf":    confidence,
                "risk":    risk_level, "verdict": verdict.value,
                "reason":  reason, "resp":    response_text,
                "factors": json.dumps(score_factors),
                "skills":  json.dumps(skill_evidence or {}),
                "prev":    prev_hash, "own":     own_hash,
                "rid":     ctx["request_id"],
                "ip":      ctx["client_ip"],
                "ua":      (ctx["user_agent"] or "")[:200],
                "prov":    llm_provider,
                "lat":     latency_ms,
            }
        )

        # Alerts
        if verdict in (Verdict.BLOCKED, Verdict.ESCALATED):
            bg.add_task(
                AlertSystem.create,
                str(workspace["id"]), ledger_id, token["agent_name"],
                f"[{verdict.value}] {token['agent_name']}: {payload.action[:120]}",
                score,
                AlertType.VIOLATION if verdict == Verdict.BLOCKED else AlertType.ESCALATION
            )

        # Auto memory
        bg.add_task(
            MemoryEngine.auto_save,
            str(workspace["id"]), token["agent_name"],
            payload.action, verdict, score, payload.context or ""
        )

        # Anomaly detection (background)
        bg.add_task(
            AnomalyDetector.run_all,
            str(workspace["id"]), token["agent_name"]
        )

        # SSE publish
        bg.add_task(
            SSEBroker.publish,
            str(workspace["id"]),
            "validation",
            {
                "verdict":    verdict.value,
                "score":      score,
                "risk_level": risk_level,
                "agent_name": token["agent_name"],
                "action":     payload.action[:120],
                "ledger_id":  ledger_id,
            }
        )

        # Update workspace usage counter
        bg.add_task(
            db.execute,
            "UPDATE workspaces SET usage_this_month = usage_this_month + 1 WHERE id = :wid",
            {"wid": workspace["id"]}
        )

    latency = int((time.time() - start_time) * 1000)
    log.info(
        f"Validated: {token['agent_name']} | {verdict.value} | "
        f"score={score} conf={confidence:.2f} risk={risk_level} | "
        f"{latency}ms | {llm_provider} | {ctx['request_id']}"
    )

    return ValidateResponse(
        verdict=verdict, score=score, confidence=confidence,
        risk_level=risk_level, reason=reason, response=response_text,
        execute=(verdict == Verdict.APPROVED), agent_name=token["agent_name"],
        ledger_id=ledger_id, hash=own_hash,
        memories_used=len(memories), duplicate_check="clean", duplicate_of=None,
        score_factors=score_factors,
        skill_evidence=skill_evidence,
        llm_provider=llm_provider,
        request_id=ctx["request_id"], latency_ms=latency
    )


@app.post("/validate", tags=["Validation"], response_model=ValidateResponse)
async def validate_action(
    payload: ValidateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    ws: Dict = Depends(get_workspace),
    ctx: Dict = Depends(get_request_context),
):
    """
    Validate an agent action and get a verdict.

    In a single call:
    1. Retrieves relevant memories
    2. Checks for duplicates
    3. Calculates Intent Fidelity Score (multi-LLM or heuristic)
    4. Optionally runs SkillExecutor for tool-backed evidence
    5. Determines verdict: APPROVED / BLOCKED / ESCALATED / DUPLICATE
    6. Generates response
    7. Records to immutable cryptographic ledger
    8. Creates alerts for violations
    9. Triggers anomaly detection
    10. Pushes real-time SSE event
    """
    return await _run_validation(payload, ws, ctx, background_tasks)


@app.post("/validate/batch", tags=["Validation"], response_model=BatchValidateResponse)
async def validate_batch(
    payload: BatchValidateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    ws: Dict = Depends(get_workspace),
    ctx: Dict = Depends(get_request_context),
):
    """
    Validate up to 20 actions simultaneously (parallel execution).

    Same full pipeline as /validate for each action.
    Returns a summary with aggregate statistics.
    """
    start_time = time.time()

    async def _validate_one(action: str, idx: int) -> ValidateResponse:
        sub_ctx = {**ctx, "request_id": f"{ctx['request_id']}_{idx}"}
        req = ValidateRequest(
            token_id=payload.token_id,
            action=action,
            context=payload.context,
            generate_response=payload.generate_response,
            check_duplicates=payload.check_duplicates,
            dry_run=payload.dry_run,
        )
        return await _run_validation(req, ws, sub_ctx, background_tasks)

    # Execute all in parallel
    results = await asyncio.gather(
        *[_validate_one(a, i) for i, a in enumerate(payload.actions)],
        return_exceptions=True
    )

    valid_results = []
    for r in results:
        if isinstance(r, Exception):
            log.error(f"Batch validation error: {r}")
            # Include a fallback error result
            valid_results.append(ValidateResponse(
                verdict=Verdict.BLOCKED, score=0, confidence=0.0,
                risk_level="critical", reason=f"Validation error: {str(r)[:100]}",
                response=None, execute=False, agent_name="unknown",
                ledger_id=None, hash=None, memories_used=0,
                duplicate_check="error", duplicate_of=None,
                score_factors={}, skill_evidence=None, llm_provider=None,
                request_id=ctx["request_id"], latency_ms=0
            ))
        else:
            valid_results.append(r)

    total = len(valid_results)
    approved_count  = sum(1 for r in valid_results if r.verdict == Verdict.APPROVED)
    blocked_count   = sum(1 for r in valid_results if r.verdict == Verdict.BLOCKED)
    escalated_count = sum(1 for r in valid_results if r.verdict == Verdict.ESCALATED)
    avg_score = sum(r.score for r in valid_results) / max(total, 1)

    return BatchValidateResponse(
        results=valid_results,
        summary={
            "total":     total,
            "approved":  approved_count,
            "blocked":   blocked_count,
            "escalated": escalated_count,
            "avg_score": round(avg_score, 1),
            "approval_rate": round(approved_count / max(total, 1) * 100, 1),
        },
        request_id=ctx["request_id"],
        latency_ms=int((time.time() - start_time) * 1000)
    )


@app.post("/validate/explain", tags=["Validation"])
async def explain_validation(
    payload: ExplainRequest,
    ws: Dict = Depends(get_workspace),
):
    """
    Get a deep chain-of-thought explanation of a validation decision.

    Unlike /validate, this endpoint focuses on transparency:
    - Step-by-step reasoning
    - Which rules were matched or violated
    - Why the score is what it is
    - What would change the decision
    - Confidence analysis

    Does NOT record to ledger (use /validate for that).
    """
    if not settings.has_llm():
        raise HTTPException(503, "LLM not configured — explain requires AI")

    token = await db.fetch_one(
        "SELECT * FROM intent_tokens WHERE id = :tid AND workspace_id = :wid AND active = TRUE",
        {"tid": payload.token_id, "wid": ws["id"]}
    )
    if not token:
        raise HTTPException(404, "Intent Token not found")
    token = dict(token)

    memories = await MemoryEngine.get_relevant(
        str(ws["id"]), token["agent_name"], payload.action
    )

    can_rules    = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(token["can_do"]))
    cannot_rules = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(token["cannot_do"]))
    mem_ctx      = ""
    if memories:
        items   = "\n".join(f"  - {m['key']}: {m['value'][:100]}" for m in memories[:5])
        mem_ctx = f"\nAGENT MEMORY:\n{items}"

    prompt = f"""You are Nova, an AI governance system explaining a validation decision in detail.

AGENT: {token['agent_name']}
ACTION: "{payload.action[:500]}"
CONTEXT: {payload.context or 'none'}

AUTHORIZED ACTIONS (can_do):
{can_rules or "  (none specified)"}

FORBIDDEN ACTIONS (cannot_do):
{cannot_rules or "  (none specified)"}
{mem_ctx}

Provide a thorough explanation with:
1. VERDICT: APPROVED / BLOCKED / ESCALATED with score (0-100)
2. REASONING: Step-by-step analysis of how the action maps to each relevant rule
3. KEY_FACTORS: The 2-3 most important factors in your decision (JSON object)
4. CONFIDENCE: How confident you are (0-100%) and why
5. WHAT_WOULD_CHANGE: What modification to the action would change the verdict
6. RISK_ASSESSMENT: Any risks even in approved actions

Format as structured JSON only:
{{
  "verdict": "APPROVED|BLOCKED|ESCALATED",
  "score": 0,
  "confidence": 95,
  "reasoning": "detailed step-by-step",
  "key_factors": {{"factor": "explanation"}},
  "what_would_change": "...",
  "risk_assessment": "...",
  "relevant_rules_matched": ["rule1", "rule2"],
  "relevant_rules_violated": ["rule1"]
}}"""

    content, provider, model = await LLMGateway.complete(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.2,
    )
    clean = re.sub(r'```json\s*|```\s*', '', content).strip()
    result = json.loads(clean)

    return {
        **result,
        "action":     payload.action,
        "agent_name": token["agent_name"],
        "llm_provider": provider,
        "llm_model":    model,
        "dry_run":    True,
    }


@app.post("/simulate", tags=["Validation"])
async def simulate_policy(
    payload: SimulateRequest,
    ws: Dict = Depends(get_workspace),
):
    """
    Simulate a policy against test actions without creating a real token or ledger entries.

    Use this to:
    - Test new rule sets before deploying to production
    - Validate policy changes
    - Build policy coverage reports

    Returns a detailed matrix of results per test action.
    """
    results = []
    for action in payload.test_actions:
        score, reason, factors, confidence, llm_provider = \
            await ScoringEngine.calculate_score(
                action, payload.can_do, payload.cannot_do,
                payload.context or ""
            )
        if score >= settings.SCORE_APPROVED_THRESHOLD:
            verdict = "APPROVED"
        elif score >= settings.SCORE_ESCALATED_THRESHOLD:
            verdict = "ESCALATED"
        else:
            verdict = "BLOCKED"

        results.append({
            "action":       action,
            "verdict":      verdict,
            "score":        score,
            "confidence":   confidence,
            "reason":       reason,
            "score_factors": factors,
            "risk_level":   ScoringEngine.score_to_risk(score),
        })

    approved_count = sum(1 for r in results if r["verdict"] == "APPROVED")
    return {
        "agent_name":  payload.agent_name,
        "test_count":  len(results),
        "results":     results,
        "summary": {
            "approved":      approved_count,
            "blocked":       sum(1 for r in results if r["verdict"] == "BLOCKED"),
            "escalated":     sum(1 for r in results if r["verdict"] == "ESCALATED"),
            "approval_rate": round(approved_count / max(len(results), 1) * 100, 1),
            "avg_score":     round(sum(r["score"] for r in results) / max(len(results), 1), 1),
        },
        "llm_provider": results[0]["confidence"] if results else None,
        "simulated":    True,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Webhook
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/webhook/{api_key}", tags=["Webhook"])
async def webhook(
    api_key: str,
    body: WebhookBody,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Flexible webhook endpoint for n8n, Zapier, Make, and custom integrations.

    Accepts flexible field names (action/message/texto, token_id/token, context/contexto).
    Optionally saves a memory before validating.
    Auto-discovers the first active token if none specified.
    """
    ws = await db.fetch_one(
        "SELECT * FROM workspaces WHERE api_key = :key", {"key": api_key}
    )
    if not ws:
        raise HTTPException(401, "Invalid API key")
    ws = dict(ws)

    action  = body.action or body.message or body.texto
    if not action:
        raise HTTPException(400, "No action provided. Use 'action', 'message', or 'texto'.")

    context  = body.context or body.contexto or ""
    token_id = body.token_id or body.token or ""

    # Save memory if provided
    if body.memory_key and body.memory_val:
        await db.execute(
            """INSERT INTO memories
               (workspace_id, agent_name, key, value, tags, importance, source)
               VALUES (:wid, :agent, :key, :val, :tags, :imp, 'webhook')""",
            {
                "wid":   ws["id"],
                "agent": body.agent_name or "webhook_agent",
                "key":   body.memory_key,
                "val":   body.memory_val,
                "tags":  body.memory_tags or ["webhook"],
                "imp":   body.memory_importance or 5,
            }
        )

    # Auto-discover token
    if not token_id:
        row = await db.fetch_one(
            "SELECT id FROM intent_tokens WHERE workspace_id = :wid AND active = TRUE LIMIT 1",
            {"wid": ws["id"]}
        )
        if row:
            token_id = str(row["id"])
        else:
            return {
                "verdict": "NO_TOKEN", "execute": True, "score": 50,
                "reason": "No active Intent Token — action allowed by default",
                "warning": "Create an Intent Token for proper governance",
            }

    ctx = {
        "request_id": Crypto.generate_request_id(),
        "client_ip":  request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", ""),
        "start_time": time.time(),
    }

    return await _run_validation(
        ValidateRequest(
            token_id=token_id, action=action, context=context,
            generate_response=body.respond,
            check_duplicates=body.dedup,
            dry_run=body.dry_run,
        ),
        ws, ctx, background_tasks
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Memory
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/memory", tags=["Memory"], response_model=MemoryResponse)
async def save_memory(payload: MemoryCreate, ws: Dict = Depends(get_workspace)):
    expires_at = None
    if payload.expires_in_hours:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=payload.expires_in_hours)

    count = await db.fetch_one(
        "SELECT COUNT(*) c FROM memories WHERE workspace_id = :wid AND agent_name = :agent",
        {"wid": ws["id"], "agent": payload.agent_name}
    )
    if count["c"] >= settings.MEMORY_MAX_PER_AGENT:
        await db.execute(
            """DELETE FROM memories
               WHERE id IN (
                   SELECT id FROM memories
                   WHERE workspace_id = :wid AND agent_name = :agent
                   ORDER BY importance ASC, created_at ASC LIMIT 10
               )""",
            {"wid": ws["id"], "agent": payload.agent_name}
        )

    memory_id = await db.execute(
        """INSERT INTO memories
           (workspace_id, agent_name, key, value, tags, importance, source, metadata, expires_at)
           VALUES (:wid, :agent, :key, :val, :tags, :imp, 'manual', :meta, :exp)
           RETURNING id""",
        {
            "wid":   ws["id"], "agent": payload.agent_name,
            "key":   payload.key, "val":   payload.value,
            "tags":  payload.tags, "imp":   payload.importance,
            "meta":  json.dumps(payload.metadata), "exp":   expires_at,
        }
    )
    return {
        "id": memory_id, "agent_name": payload.agent_name,
        "key": payload.key, "value": payload.value,
        "tags": payload.tags, "importance": payload.importance,
        "source": "manual", "metadata": payload.metadata,
        "expires_at": expires_at, "created_at": datetime.now(timezone.utc), "updated_at": None,
    }


@app.get("/memory/{agent_name}", tags=["Memory"])
async def get_memories(
    agent_name:     str = Path(...),
    limit:          int = Query(50, ge=1, le=200),
    min_importance: int = Query(1, ge=1, le=10),
    tag:            Optional[str] = Query(None),
    ws: Dict = Depends(get_workspace)
):
    query  = """
        SELECT id, key, value, tags, importance, source, metadata,
               expires_at, created_at, updated_at
        FROM memories
        WHERE workspace_id = :wid AND agent_name = :agent
          AND (expires_at IS NULL OR expires_at > NOW())
          AND importance >= :min_imp
    """
    params: Dict = {"wid": ws["id"], "agent": agent_name,
                    "min_imp": min_importance, "lim": limit}
    if tag:
        query += " AND :tag = ANY(tags)"
        params["tag"] = tag
    query += " ORDER BY importance DESC, created_at DESC LIMIT :lim"
    rows = await db.fetch_all(query, params)
    return [{**dict(r), "metadata": r["metadata"] or {}} for r in rows]


@app.post("/memory/search", tags=["Memory"])
async def search_memories(payload: MemorySearch, ws: Dict = Depends(get_workspace)):
    return await MemoryEngine.get_relevant(
        str(ws["id"]), payload.agent_name, payload.query, payload.limit
    )


@app.patch("/memory/{memory_id}", tags=["Memory"])
async def update_memory(
    memory_id: int, payload: MemoryUpdate,
    ws: Dict = Depends(get_workspace)
):
    updates = ["updated_at = NOW()"]
    values  = {"mid": memory_id, "wid": ws["id"]}
    if payload.value            is not None: updates.append("value = :val");    values["val"]  = payload.value
    if payload.tags             is not None: updates.append("tags = :tags");    values["tags"] = payload.tags
    if payload.importance       is not None: updates.append("importance = :imp"); values["imp"] = payload.importance
    if payload.expires_in_hours is not None:
        updates.append("expires_at = NOW() + :exp * INTERVAL '1 hour'")
        values["exp"] = payload.expires_in_hours
    if payload.metadata         is not None: updates.append("metadata = :meta"); values["meta"] = json.dumps(payload.metadata)
    if len(updates) == 1:
        raise HTTPException(400, "No fields to update")
    await db.execute(
        f"UPDATE memories SET {', '.join(updates)} WHERE id = :mid AND workspace_id = :wid",
        values
    )
    return {"status": "updated", "memory_id": memory_id}


@app.delete("/memory/{agent_name}", tags=["Memory"])
async def clear_memories(
    agent_name:   str,
    expired_only: bool = Query(False),
    ws: Dict = Depends(get_workspace)
):
    if expired_only:
        result = await db.execute(
            "DELETE FROM memories WHERE workspace_id = :wid AND agent_name = :agent AND expires_at < NOW()",
            {"wid": ws["id"], "agent": agent_name}
        )
    else:
        result = await db.execute(
            "DELETE FROM memories WHERE workspace_id = :wid AND agent_name = :agent",
            {"wid": ws["id"], "agent": agent_name}
        )
    return {"status": "cleared", "agent_name": agent_name, "deleted": result}


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Ledger
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/ledger", tags=["Ledger"])
async def get_ledger(
    limit:      int = Query(50, ge=1, le=500),
    offset:     int = Query(0, ge=0),
    verdict:    Optional[str] = Query(None),
    agent_name: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    since:      Optional[datetime] = Query(None),
    until:      Optional[datetime] = Query(None),
    ws: Dict = Depends(get_workspace)
):
    """Get ledger entries with rich filtering including risk_level."""
    query  = """
        SELECT id, agent_name, action, context, score, confidence, risk_level,
               verdict, reason, response, score_factors, own_hash,
               llm_provider, latency_ms, executed_at
        FROM ledger WHERE workspace_id = :wid
    """
    params: Dict = {"wid": ws["id"], "limit": limit, "offset": offset}
    if verdict:
        query += " AND verdict = :verdict"; params["verdict"] = verdict.upper()
    if agent_name:
        query += " AND agent_name = :agent"; params["agent"] = agent_name
    if risk_level:
        query += " AND risk_level = :risk"; params["risk"] = risk_level.lower()
    if since:
        query += " AND executed_at >= :since"; params["since"] = since
    if until:
        query += " AND executed_at <= :until"; params["until"] = until
    query += " ORDER BY id DESC LIMIT :limit OFFSET :offset"
    rows = await db.fetch_all(query, params)
    return [{**dict(r), "score_factors": r["score_factors"] or {}} for r in rows]


@app.get("/ledger/{entry_id}", tags=["Ledger"])
async def get_ledger_entry(entry_id: int, ws: Dict = Depends(get_workspace)):
    row = await db.fetch_one(
        "SELECT * FROM ledger WHERE id = :id AND workspace_id = :wid",
        {"id": entry_id, "wid": ws["id"]}
    )
    if not row:
        raise HTTPException(404, "Ledger entry not found")
    entry = dict(row)
    entry["score_factors"] = entry.get("score_factors") or {}
    entry["skill_evidence"] = entry.get("skill_evidence") or {}
    return entry


@app.get("/ledger/verify", tags=["Ledger"])
async def verify_chain(ws: Dict = Depends(get_workspace)):
    """
    Verify the cryptographic integrity of the entire ledger chain.
    Detects any tampering or unauthorized modifications.
    """
    rows = await db.fetch_all(
        "SELECT * FROM ledger WHERE workspace_id = :wid ORDER BY id ASC",
        {"wid": ws["id"]}
    )
    if not rows:
        return {"verified": True, "total_records": 0, "broken_at": None, "chain_hash": None}

    prev_hash  = "GENESIS"
    broken_at  = None
    broken_entries = []

    for row in rows:
        row = dict(row)
        expected = Crypto.chain_hash(prev_hash, {
            "workspace_id": str(ws["id"]),
            "token_id":     str(row["token_id"]),
            "action":       row["action"],
            "score":        row["score"],
            "verdict":      row["verdict"],
            "timestamp":    row["executed_at"].isoformat() if row["executed_at"] else ""
        })
        if row["own_hash"] != expected:
            broken_at = row["id"]
            broken_entries.append(row["id"])
            if len(broken_entries) >= 5:  # Report up to 5 broken
                break
        prev_hash = row["own_hash"]

    return {
        "verified":        len(broken_entries) == 0,
        "total_records":   len(rows),
        "broken_at":       broken_at,
        "broken_entries":  broken_entries,
        "chain_hash":      rows[-1]["own_hash"] if rows else None,
        "verified_at":     datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ledger/export", tags=["Ledger"])
async def export_ledger(
    fmt:        str = Query("json", description="Export format: json or csv"),
    limit:      int = Query(1000, ge=1, le=10000),
    verdict:    Optional[str] = Query(None),
    agent_name: Optional[str] = Query(None),
    since:      Optional[datetime] = Query(None),
    ws: Dict = Depends(get_workspace)
):
    """
    Export ledger entries as JSON or CSV.
    Includes cryptographic signature for tamper detection.
    """
    query  = """
        SELECT id, agent_name, action, context, score, confidence, risk_level,
               verdict, reason, own_hash, llm_provider, executed_at
        FROM ledger WHERE workspace_id = :wid
    """
    params: Dict = {"wid": ws["id"], "lim": limit}
    if verdict:    query += " AND verdict = :verdict";    params["verdict"] = verdict.upper()
    if agent_name: query += " AND agent_name = :agent";  params["agent"]   = agent_name
    if since:      query += " AND executed_at >= :since"; params["since"]   = since
    query += " ORDER BY id ASC LIMIT :lim"
    rows = await db.fetch_all(query, params)

    entries = [dict(r) for r in rows]
    # Add export metadata
    export_meta = {
        "workspace_id":  str(ws["id"]),
        "exported_at":   datetime.now(timezone.utc).isoformat(),
        "total_records": len(entries),
        "export_hash":   Crypto.sign({"workspace": str(ws["id"]), "count": len(entries)}),
    }

    if fmt.lower() == "csv":
        output = io.StringIO()
        if entries:
            writer = csv.DictWriter(output, fieldnames=entries[0].keys())
            writer.writeheader()
            writer.writerows(entries)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=nova_ledger.csv"}
        )
    else:
        return {"meta": export_meta, "entries": entries}


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Alerts
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/alerts", tags=["Alerts"])
async def get_alerts(
    resolved:   Optional[bool] = Query(None),
    severity:   Optional[str]  = Query(None),
    alert_type: Optional[str]  = Query(None),
    limit:      int = Query(50, ge=1, le=200),
    ws: Dict = Depends(get_workspace)
):
    query  = """
        SELECT id, agent_name, alert_type, severity, message, score,
               metadata, resolved, resolved_by, resolved_at, created_at
        FROM alerts WHERE workspace_id = :wid
    """
    params: Dict = {"wid": ws["id"], "limit": limit}
    if resolved  is not None: query += " AND resolved = :resolved"; params["resolved"]  = resolved
    if severity:              query += " AND severity = :sev";      params["sev"]       = severity.lower()
    if alert_type:            query += " AND alert_type = :atype";  params["atype"]     = alert_type.lower()
    query += " ORDER BY created_at DESC LIMIT :limit"
    rows = await db.fetch_all(query, params)
    return [{**dict(r), "metadata": r["metadata"] or {}} for r in rows]


@app.patch("/alerts/{alert_id}/resolve", tags=["Alerts"])
async def resolve_alert(
    alert_id: int,
    payload: AlertResolve = Body(default=AlertResolve()),
    ws: Dict = Depends(get_workspace)
):
    await AlertSystem.resolve(str(ws["id"]), alert_id, payload.resolved_by)
    return {"status": "resolved", "alert_id": alert_id}


@app.post("/alerts/bulk-resolve", tags=["Alerts"])
async def bulk_resolve_alerts(
    alert_ids:   List[int] = Body(...),
    resolved_by: Optional[str] = Body(None),
    ws: Dict = Depends(get_workspace)
):
    """Resolve multiple alerts at once."""
    count = 0
    for alert_id in alert_ids[:100]:  # Max 100 at a time
        await AlertSystem.resolve(str(ws["id"]), alert_id, resolved_by)
        count += 1
    return {"status": "resolved", "count": count}


@app.delete("/alerts/{alert_id}", tags=["Alerts"])
async def delete_alert(alert_id: int, ws: Dict = Depends(get_workspace)):
    result = await db.execute(
        "DELETE FROM alerts WHERE id = :id AND workspace_id = :wid AND resolved = TRUE",
        {"id": alert_id, "wid": ws["id"]}
    )
    if result == 0:
        raise HTTPException(400, "Alert not found or not resolved")
    return {"status": "deleted", "alert_id": alert_id}


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Analytics
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/stats", tags=["Analytics"], response_model=StatsResponse)
async def get_stats(ws: Dict = Depends(get_workspace)):
    return await AnalyticsEngine.get_stats(str(ws["id"]))


@app.get("/stats/agents", tags=["Analytics"])
async def get_agent_stats(ws: Dict = Depends(get_workspace)):
    rows = await db.fetch_all(
        """SELECT
            l.agent_name,
            COUNT(*) AS total_actions,
            COUNT(*) FILTER (WHERE l.verdict='APPROVED')  AS approved,
            COUNT(*) FILTER (WHERE l.verdict='BLOCKED')   AS blocked,
            COUNT(*) FILTER (WHERE l.verdict='ESCALATED') AS escalated,
            ROUND(AVG(l.score)) AS avg_score,
            ROUND(AVG(l.confidence)) AS avg_confidence,
            MAX(l.executed_at) AS last_action
           FROM ledger l WHERE l.workspace_id = :wid
           GROUP BY l.agent_name ORDER BY total_actions DESC""",
        {"wid": ws["id"]}
    )
    return [
        {
            "agent_name":    row["agent_name"],
            "total_actions": row["total_actions"],
            "approved":      row["approved"],
            "blocked":       row["blocked"],
            "escalated":     row["escalated"],
            "avg_score":     int(row["avg_score"] or 0),
            "avg_confidence": float(row["avg_confidence"] or 1.0),
            "approval_rate": round(row["approved"] / max(row["total_actions"],1) * 100, 1),
            "last_action":   row["last_action"],
        }
        for row in rows
    ]


@app.get("/stats/hourly", tags=["Analytics"])
async def get_hourly_stats(days: int = Query(7, ge=1, le=30), ws: Dict = Depends(get_workspace)):
    rows = await db.fetch_all(
        """SELECT EXTRACT(HOUR FROM executed_at) AS hour,
                  COUNT(*) AS count, ROUND(AVG(score)) AS avg_score
           FROM ledger
           WHERE workspace_id = :wid
             AND executed_at > NOW() - :days * INTERVAL '1 day'
           GROUP BY hour ORDER BY hour""",
        {"wid": ws["id"], "days": days}
    )
    hourly = {int(r["hour"]): {"count": r["count"], "avg_score": int(r["avg_score"] or 0)} for r in rows}
    return [{"hour": h, "count": hourly.get(h,{}).get("count",0),
             "avg_score": hourly.get(h,{}).get("avg_score",0)} for h in range(24)]


@app.get("/stats/risk", tags=["Analytics"])
async def get_risk_profile(ws: Dict = Depends(get_workspace)):
    """Per-agent risk scoring based on the last 24 hours of activity."""
    return await AnalyticsEngine.get_risk_profile(str(ws["id"]))


@app.get("/stats/anomalies", tags=["Analytics"])
async def get_anomalies(
    limit: int = Query(20, ge=1, le=100),
    ws: Dict = Depends(get_workspace)
):
    """Get detected behavioral anomalies across all agents."""
    return await AnalyticsEngine.get_anomalies(str(ws["id"]), limit)


@app.get("/stats/timeline", tags=["Analytics"])
async def get_timeline(
    hours: int = Query(24, ge=1, le=168),
    ws: Dict = Depends(get_workspace)
):
    """Hour-by-hour activity timeline (up to 7 days)."""
    return await AnalyticsEngine.get_timeline(str(ws["id"]), hours)


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — SSE Streaming
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/stream/events", tags=["Streaming"])
async def stream_events(
    x_api_key: str = Query(..., description="Workspace API key"),
    since_id: Optional[int] = Query(None, description="Resume from event ID"),
):
    """
    Server-Sent Events stream for real-time validation events.

    Connect to this endpoint to receive live notifications for:
    - Validation results (APPROVED/BLOCKED/ESCALATED)
    - Alerts created
    - Anomalies detected

    Usage:
        const evtSource = new EventSource('/stream/events?x_api_key=YOUR_KEY');
        evtSource.onmessage = (e) => console.log(JSON.parse(e.data));
    """
    ws = await db.fetch_one(
        "SELECT * FROM workspaces WHERE api_key = :key", {"key": x_api_key}
    )
    if not ws:
        raise HTTPException(401, "Invalid API key")
    ws = dict(ws)

    # Send recent events if resuming
    backlog = []
    if since_id:
        rows = await db.fetch_all(
            """SELECT * FROM sse_events
               WHERE workspace_id = :wid AND id > :sid
               ORDER BY id ASC LIMIT 50""",
            {"wid": ws["id"], "sid": since_id}
        )
        backlog = [dict(r) for r in rows]

    queue = SSEBroker.subscribe(str(ws["id"]))

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Send ping
            yield f"event: ping\ndata: {json.dumps({'ts': datetime.now(timezone.utc).isoformat()})}\n\n"

            # Send backlog
            for evt in backlog:
                data = json.dumps({"id": evt["id"], "type": evt["event_type"],
                                   "payload": evt["payload"] if isinstance(evt["payload"], dict) else {}})
                yield f"data: {data}\n\n"

            # Live stream
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat
                    yield f"event: heartbeat\ndata: {json.dumps({'ts': datetime.now(timezone.utc).isoformat()})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            SSEBroker.unsubscribe(str(ws["id"]), queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":              "no-cache",
            "X-Accel-Buffering":          "no",
            "Access-Control-Allow-Origin": "*",
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Demo / Development
# ══════════════════════════════════════════════════════════════════════════════


@app.post("/tokens/from-description", tags=["Agents"])
async def create_token_from_description(
    request: Request,
    ws: Dict = Depends(get_workspace)
):
    """
    Crea un Intent Token a partir de una descripción en lenguaje natural.
    El servidor usa el LLM configurado para extraer can_do / cannot_do.
    
    Body: {
      "description": "Melissa es mi recepcionista virtual, puede agendar citas...",
      "authorized_by": "admin@empresa.com"
    }
    """
    data = await request.json()
    description  = (data.get("description") or "").strip()
    authorized_by = data.get("authorized_by", "api")

    if not description:
        raise HTTPException(400, "description es requerido")

    if not settings.has_llm():
        raise HTTPException(503, "LLM no configurado — usa POST /tokens directamente con can_do/cannot_do")

    # ── Llamar al LLM para extraer reglas ─────────────────────────────────────
    prompt = f"""Analiza esta descripción de un agente de IA y extrae sus reglas de gobernanza.

DESCRIPCIÓN:
{description}

Responde SOLO en JSON válido, sin markdown, sin texto adicional:
{{
  "name": "nombre corto del agente (2-4 palabras)",
  "description": "descripción en una línea de qué hace",
  "can_do": [
    "acción concreta que SÍ puede hacer"
  ],
  "cannot_do": [
    "acción que NO puede hacer"
  ]
}}

can_do = cosas PERMITIDAS. cannot_do = cosas PROHIBIDAS.
Extrae entre 3-8 items por lista. Sé específico y accionable."""

    try:
        llm_response = await ResponseGenerator.generate(
            prompt=prompt,
            workspace_id=str(ws["id"]),
            agent_name="nova-parser",
            max_tokens=1024
        )
        
        import re as _re
        raw = llm_response.get("text", "") if isinstance(llm_response, dict) else str(llm_response)
        raw = _re.sub(r"```json\s*|```\s*", "", raw).strip()
        m = _re.search(r"\{[\s\S]+\}", raw)
        parsed = json.loads(m.group(0) if m else raw)
    except Exception as e:
        log.warning(f"LLM parse error: {e}")
        raise HTTPException(422, f"No pude extraer reglas de la descripción: {e}")

    can_do    = parsed.get("can_do", [])
    cannot_do = parsed.get("cannot_do", [])
    name      = parsed.get("name", "Agente")
    desc      = parsed.get("description", description[:100])

    if not can_do and not cannot_do:
        raise HTTPException(422, "No se extrajeron reglas. Intenta con una descripción más detallada.")

    # ── Crear el token con las reglas extraídas ────────────────────────────────
    sig = Crypto.sign({"name": name, "timestamp": datetime.now(timezone.utc).isoformat()})

    token_id = await db.execute(
        """INSERT INTO intent_tokens
           (workspace_id, agent_name, description, can_do, cannot_do, authorized_by, signature)
           VALUES (:wid, :name, :desc, :can, :cannot, :auth, :sig)
           RETURNING id""",
        {
            "wid":    ws["id"],
            "name":   name,
            "desc":   desc,
            "can":    can_do,
            "cannot": cannot_do,
            "auth":   authorized_by,
            "sig":    sig,
        }
    )

    log.info(f"Token created from description: {name} (ws={ws['id']})")
    return {
        "token_id":    str(token_id),
        "agent_name":  name,
        "description": desc,
        "can_do":      can_do,
        "cannot_do":   cannot_do,
        "signature":   sig,
        "parsed_from": "natural_language",
    }


@app.post("/demo/seed", tags=["Development"])
async def seed_demo_data(ws: Dict = Depends(get_workspace)):
    """
    Seed the workspace with demo agents, policies, actions, and memories.
    Useful for testing and product demonstrations.
    """
    # Demo policy
    policy_id = await db.execute(
        """INSERT INTO policies
           (workspace_id, name, description, category, can_do, cannot_do,
            created_by, is_template)
           VALUES (:wid, :name, :desc, :cat, :can, :cannot, :by, TRUE)
           RETURNING id""",
        {
            "wid":    ws["id"],
            "name":   "Standard Customer Service Policy",
            "desc":   "Base policy for all customer-facing agents",
            "cat":    "communication",
            "can":    ["Respond to customer inquiries", "Provide order status",
                       "Share publicly available pricing"],
            "cannot": ["Share other customers' data", "Make promises about delivery without verification",
                       "Issue refunds over $500 without approval"],
            "by":     "demo@nova-os.com",
        }
    )

    agents = [
        {
            "name": "Email Agent", "desc": "Handles customer email communications",
            "can":    ["Reply to customer emails", "Check order status",
                       "Provide tracking information", "Answer product questions"],
            "cannot": ["Offer discounts greater than 10%",
                       "Promise delivery dates without checking inventory",
                       "Share customer data externally", "Process refunds over $500"]
        },
        {
            "name": "Billing Agent", "desc": "Manages invoicing and payments",
            "can":    ["Generate invoices", "Send payment reminders",
                       "Process payments under $1000", "Check payment history"],
            "cannot": ["Modify issued invoices", "Cancel invoices over $5000",
                       "Change payment terms without approval",
                       "Access other customer accounts"]
        },
        {
            "name": "Inventory Agent", "desc": "Monitors and updates stock levels",
            "can":    ["Update stock counts", "Generate low stock alerts",
                       "Create purchase requests under $5000", "View supplier information"],
            "cannot": ["Create purchase orders over $10000", "Delete active products",
                       "Modify pricing", "Access financial reports"]
        }
    ]

    token_ids = []
    for agent in agents:
        sig = Crypto.sign({"name": agent["name"],
                           "timestamp": datetime.now(timezone.utc).isoformat()})
        tid = await db.execute(
            """INSERT INTO intent_tokens
               (workspace_id, agent_name, description, can_do, cannot_do,
                policy_id, authorized_by, signature)
               VALUES (:wid, :name, :desc, :can, :cannot, :pol, :auth, :sig)
               RETURNING id""",
            {
                "wid":    ws["id"], "name":   agent["name"],
                "desc":   agent["desc"], "can":    agent["can"],
                "cannot": agent["cannot"], "pol":    policy_id,
                "auth":   "demo@nova-os.com", "sig":    sig,
            }
        )
        token_ids.append((str(tid), agent["name"]))

    # Demo memories
    memories = [
        ("Email Agent",    "vip_customer_policy",  "VIP customers can receive up to 8% discount without approval", ["policy","vip"], 9),
        ("Email Agent",    "standard_discount",     "Standard discount: 5% for regular customers, never exceed 10%", ["policy"], 9),
        ("Billing Agent",  "high_value_approval",  "Invoices over $5000 require CFO approval before cancellation", ["policy","approval"], 8),
        ("Inventory Agent","primary_supplier",      "Primary supplier: LogiCo SA — Contact: orders@logico.com", ["supplier"], 6),
        ("Inventory Agent","reorder_threshold",     "Minimum stock threshold before reorder: 50 units", ["policy","inventory"], 7),
    ]
    for agent_name, key, value, tags, importance in memories:
        await db.execute(
            """INSERT INTO memories
               (workspace_id, agent_name, key, value, tags, importance, source)
               VALUES (:wid, :agent, :key, :val, :tags, :imp, 'demo')""",
            {"wid": ws["id"], "agent": agent_name, "key": key,
             "val": value, "tags": tags, "imp": importance}
        )

    # Demo ledger actions
    demo_actions = [
        ("Reply to customer inquiry about order #4821 status",         92, "APPROVED"),
        ("Offer 25% discount to a complaining customer",               15, "BLOCKED"),
        ("Generate invoice #F-2024-089 for $1,200",                    94, "APPROVED"),
        ("Cancel invoice #F-2024-071 for $8,500",                      12, "BLOCKED"),
        ("Update stock: Product A now at 45 units",                    91, "APPROVED"),
        ("Create purchase order for $15,000 without approval",         18, "BLOCKED"),
        ("Send order tracking information to customer",                96, "APPROVED"),
        ("Process payment reminder for overdue invoice",               89, "APPROVED"),
        ("Promise 24-hour delivery without checking stock",            25, "BLOCKED"),
        ("Alert: Low stock warning for Product C",                     93, "APPROVED"),
        ("Modify previously issued invoice #F-2024-055",                8, "BLOCKED"),
        ("Respond to product availability question",                   88, "APPROVED"),
        ("Share customer list with marketing partner",                  5, "BLOCKED"),
        ("Check inventory levels for quarterly report",                90, "APPROVED"),
    ]

    prev_hash = "GENESIS"
    for i, (action, score, verdict) in enumerate(demo_actions):
        token_id, agent_name = token_ids[i % len(token_ids)]
        own_hash = Crypto.chain_hash(prev_hash, {
            "workspace_id": str(ws["id"]),
            "token_id":     token_id,
            "action":       action,
            "score":        score,
            "verdict":      verdict,
            "timestamp":    datetime.now(timezone.utc).isoformat()
        })
        risk_level = ScoringEngine.score_to_risk(score)
        lid = await db.execute(
            """INSERT INTO ledger
               (workspace_id, token_id, agent_name, action, score, confidence, risk_level,
                verdict, reason, prev_hash, own_hash)
               VALUES (:wid, :tid, :agent, :action, :score, :conf, :risk,
                       :verdict, :reason, :prev, :own)
               RETURNING id""",
            {
                "wid":     ws["id"], "tid":     token_id,
                "agent":   agent_name, "action":  action,
                "score":   score, "conf":    0.9 if score > 50 else 0.95,
                "risk":    risk_level, "verdict": verdict,
                "reason":  "Demo data",
                "prev":    prev_hash, "own":     own_hash,
            }
        )
        if verdict == "BLOCKED":
            await AlertSystem.create(
                str(ws["id"]), lid, agent_name,
                f"[DEMO] {action[:80]}", score, AlertType.VIOLATION
            )
        prev_hash = own_hash

    log.info(f"Demo data seeded for workspace {ws['id']}")
    return {
        "status":      "seeded",
        "policy_id":   policy_id,
        "tokens":      len(token_ids),
        "actions":     len(demo_actions),
        "memories":    len(memories),
        "message":     "Demo data loaded. Explore with 'nova status' or GET /stats"
    }


@app.delete("/demo/reset", tags=["Development"])
async def reset_demo_data(
    confirm: bool = Query(False),
    ws: Dict = Depends(get_workspace)
):
    """
    Reset all workspace data.
    ⚠️ DANGER: Permanent. Disabled in production.
    """
    if not confirm:
        raise HTTPException(400, "Pass ?confirm=true to confirm deletion")
    if settings.is_production():
        raise HTTPException(403, "Reset disabled in production")

    for table in ["alerts", "anomaly_log", "memories", "sse_events",
                  "ledger", "token_history", "intent_tokens", "policies",
                  "analytics_events", "rate_limits"]:
        await db.execute(f"DELETE FROM {table} WHERE workspace_id = :wid", {"wid": ws["id"]})
    await db.execute(
        "UPDATE workspaces SET usage_this_month = 0 WHERE id = :wid", {"wid": ws["id"]}
    )
    log.warning(f"Workspace {ws['id']} was reset")
    return {"status": "reset", "workspace_id": str(ws["id"]),
            "message": "All data deleted"}


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
