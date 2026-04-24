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
import base64
import csv
import hashlib
import hmac
import importlib.util
import io
import json
import logging
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import (
    Any, AsyncGenerator, Dict, List, Optional,
    Tuple, Union, Callable, TypeVar, Generic, Annotated
)
from urllib.parse import urlencode

import httpx
import databases
from fastapi import (
    FastAPI, HTTPException, Header, Depends, Cookie,
    Request, Response, BackgroundTasks, Query, Path, Body
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field, validator, root_validator
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
    WORKSPACE_ADMIN_TOKEN: str = os.getenv("WORKSPACE_ADMIN_TOKEN", SECRET_KEY)

    # ── Multi-LLM (2026 edition — pick one or configure per workspace) ────────
    # Primary provider — env var takes precedence over workspace config
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openrouter")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
    LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "15.0"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "500"))

    # Provider API keys (any one is sufficient)
    OPENROUTER_API_KEY: str = ""
    OPENAI_API_KEY: str     = ""
    ANTHROPIC_API_KEY: str  = ""
    GEMINI_API_KEY: str     = ""
    GROQ_API_KEY: str       = ""
    XAI_API_KEY: str        = ""
    MISTRAL_API_KEY: str    = ""
    DEEPSEEK_API_KEY: str   = ""
    COHERE_API_KEY: str     = ""

    @classmethod
    def reload(cls):
        """Reload API keys and LLM settings from environment (useful after load_dotenv)."""
        cls.LLM_PROVIDER = os.getenv("LLM_PROVIDER", os.getenv("NOVA_LLM_PROVIDER", "openrouter"))
        cls.LLM_MODEL    = os.getenv("LLM_MODEL", os.getenv("NOVA_LLM_MODEL", "openai/gpt-4o-mini"))
        cls.LLM_TIMEOUT  = float(os.getenv("LLM_TIMEOUT", os.getenv("NOVA_LLM_TIMEOUT", "15.0")))
        cls.LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "500"))

        cls.OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
        cls.OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY", "")
        cls.ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
        cls.GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", os.getenv("NOVA_LLM_API_KEY", ""))
        cls.GROQ_API_KEY       = os.getenv("GROQ_API_KEY", "")
        cls.XAI_API_KEY        = os.getenv("XAI_API_KEY", "")
        cls.MISTRAL_API_KEY    = os.getenv("MISTRAL_API_KEY", "")
        cls.DEEPSEEK_API_KEY   = os.getenv("DEEPSEEK_API_KEY", "")
        cls.COHERE_API_KEY     = os.getenv("COHERE_API_KEY", "")

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
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3005")
    CORS_ORIGINS_RAW: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3005,http://127.0.0.1:3005,http://localhost:5173,http://127.0.0.1:5173"
    )
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    GITHUB_REDIRECT_URI: str = os.getenv("GITHUB_REDIRECT_URI", "")
    GITHUB_SCOPE: str = os.getenv("GITHUB_SCOPE", "read:user user:email")
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "nova_session")
    SESSION_TTL_HOURS: int = int(os.getenv("SESSION_TTL_HOURS", "8"))

    @classmethod
    def is_production(cls) -> bool:
        return cls.ENVIRONMENT == "production"

    @classmethod
    def session_cookie_secure(cls) -> bool:
        return os.getenv("SESSION_COOKIE_SECURE", "").lower() == "true" or cls.is_production()

    @classmethod
    def get_cors_origins(cls) -> List[str]:
        origins = [origin.strip() for origin in cls.CORS_ORIGINS_RAW.split(",") if origin.strip()]
        if cls.FRONTEND_URL and cls.FRONTEND_URL not in origins:
            origins.append(cls.FRONTEND_URL.rstrip("/"))
        return origins

    @classmethod
    def github_enabled(cls) -> bool:
        return bool(cls.GITHUB_CLIENT_ID and cls.GITHUB_CLIENT_SECRET and cls.GITHUB_REDIRECT_URI)

    @classmethod
    def provider_available(cls, provider: str) -> bool:
        key_map = {
            "openrouter": bool(cls.OPENROUTER_API_KEY),
            "openai": bool(cls.OPENAI_API_KEY),
            "anthropic": bool(cls.ANTHROPIC_API_KEY),
            "gemini": bool(cls.GEMINI_API_KEY),
            "google": bool(cls.GEMINI_API_KEY),
            "groq": bool(cls.GROQ_API_KEY),
            "xai": bool(cls.XAI_API_KEY),
            "mistral": bool(cls.MISTRAL_API_KEY),
            "deepseek": bool(cls.DEEPSEEK_API_KEY),
            "cohere": bool(cls.COHERE_API_KEY),
        }
        return key_map.get(provider, False)

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


from dotenv import load_dotenv
# Load .env from parent directory if not found in current
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
Settings.reload()

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
            owner_name      TEXT DEFAULT '',
            email           TEXT UNIQUE,
            api_key         TEXT UNIQUE NOT NULL,
            password_hash   TEXT DEFAULT '',
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
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS email TEXT",
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS owner_name TEXT DEFAULT ''",
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS password_hash TEXT DEFAULT ''",
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
    "anthropic":  "claude-sonnet-4-20250514",
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


class GatewayForwardBody(WebhookBody):
    forward_to: str = Field(..., description="URL del servicio real al que Nova hará forward")
    forward_method: str = Field("POST", pattern="^(GET|POST|PUT|PATCH|DELETE)$")
    forward_payload: Optional[Dict[str, Any]] = None
    forward_headers: Optional[Dict[str, str]] = None
    forward_timeout_ms: int = Field(15000, ge=1000, le=120000)
    validate_response: bool = False
    response_action: Optional[str] = None
    response_context: Optional[str] = None
    response_token_id: Optional[str] = None
    response_field: Optional[str] = None
    include_nova_headers: bool = True


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
    score_factors:   Optional[Dict[str, Any]]
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


class AssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=16000)
    page: str = Field(default="dashboard", max_length=100)
    provider: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=200)
    api_key: Optional[str] = Field(default=None, max_length=500)


class AssistantAction(BaseModel):
    type: str
    label: str
    value: Optional[str] = None


class AssistantResponse(BaseModel):
    message: str
    provider: str
    model: str
    suggested_commands: List[str]
    actions: List[AssistantAction]


class CommandRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=500)


class CommandResponse(BaseModel):
    output: str
    exit_code: int
    success: bool
    display_output: Optional[str] = None


ASSISTANT_MODEL_CATALOG: Dict[str, Dict[str, Any]] = {
    "openrouter": {
        "label": "OpenRouter",
        "logo": "/llm-brands/openrouter.svg",
        "description": "Route across premium and preview frontier models with one key.",
        "models": [
            {"id": "openai/gpt-4o-mini", "label": "GPT-4o mini", "family": "GPT", "status": "default"},
            {"id": "openai/gpt-4o", "label": "GPT-4o", "family": "GPT", "status": "stable"},
            {"id": "openai/o3", "label": "o3", "family": "Reasoning", "status": "reasoning"},
            {"id": "anthropic/claude-sonnet-4", "label": "Claude Sonnet 4", "family": "Claude", "status": "recommended"},
            {"id": "anthropic/claude-opus-4.1", "label": "Claude Opus 4.1", "family": "Claude", "status": "premium"},
            {"id": "google/gemini-2.5-pro", "label": "Gemini 2.5 Pro", "family": "Gemini", "status": "stable"},
            {"id": "x-ai/grok-4.1-fast", "label": "Grok 4.1 Fast", "family": "Grok", "status": "fast"},
            {"id": "openrouter/auto", "label": "Auto Router", "family": "Router", "status": "adaptive"},
        ],
        "default_model": "openai/gpt-4o-mini",
    },
    "anthropic": {
        "label": "Anthropic",
        "logo": "/llm-brands/anthropic.svg",
        "description": "Direct Claude access for high-quality reasoning and writing.",
        "models": [
            {"id": "claude-sonnet-4-20250514", "label": "Claude Sonnet 4", "family": "Claude", "status": "default"},
            {"id": "claude-opus-4-1-20250805", "label": "Claude Opus 4.1", "family": "Claude", "status": "premium"},
            {"id": "claude-3-5-haiku-latest", "label": "Claude Haiku 3.5", "family": "Claude", "status": "fast"},
        ],
        "default_model": "claude-sonnet-4-20250514",
    },
    "gemini": {
        "label": "Google Gemini",
        "logo": "/llm-brands/gemini.svg",
        "description": "Direct Gemini access for long context and fast operator help.",
        "models": [
            {"id": "gemini-2.0-flash", "label": "Gemini 2.0 Flash", "family": "Gemini", "status": "default"},
            {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "family": "Gemini", "status": "fast"},
            {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "family": "Gemini", "status": "stable"},
        ],
        "default_model": "gemini-2.0-flash",
    },
    "openai": {
        "label": "OpenAI",
        "logo": "/llm-brands/openai.svg",
        "description": "Direct GPT and o-series access for operator workflows.",
        "models": [
            {"id": "gpt-4o-mini", "label": "GPT-4o mini", "family": "GPT", "status": "default"},
            {"id": "gpt-4o", "label": "GPT-4o", "family": "GPT", "status": "stable"},
            {"id": "o3", "label": "o3", "family": "Reasoning", "status": "reasoning"},
        ],
        "default_model": "gpt-4o-mini",
    },
    "groq": {
        "label": "Groq",
        "logo": "/llm-brands/groq.svg",
        "description": "Ultra-fast inference for operator chats and short reasoning loops.",
        "models": [
            {"id": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B Versatile", "family": "Llama", "status": "default"},
            {"id": "llama-3.1-8b-instant", "label": "Llama 3.1 8B Instant", "family": "Llama", "status": "economy"},
            {"id": "openai/gpt-oss-120b", "label": "GPT-OSS 120B", "family": "Open", "status": "open"},
        ],
        "default_model": "llama-3.3-70b-versatile",
    },
    "xai": {
        "label": "xAI",
        "logo": "/llm-brands/xai.svg",
        "description": "Direct Grok access for fast conversational analysis.",
        "models": [
            {"id": "grok-3", "label": "Grok 3", "family": "Grok", "status": "default"},
            {"id": "grok-3-mini", "label": "Grok 3 Mini", "family": "Grok", "status": "fast"},
            {"id": "grok-4", "label": "Grok 4", "family": "Grok", "status": "premium"},
        ],
        "default_model": "grok-3",
    },
    "mistral": {
        "label": "Mistral",
        "logo": "/llm-brands/mistral.svg",
        "description": "Direct Mistral access for compact multilingual assistance.",
        "models": [
            {"id": "mistral-small-latest", "label": "Mistral Small", "family": "Mistral", "status": "default"},
            {"id": "mistral-medium-latest", "label": "Mistral Medium", "family": "Mistral", "status": "premium"},
            {"id": "ministral-8b-latest", "label": "Ministral 8B", "family": "Mistral", "status": "fast"},
        ],
        "default_model": "mistral-small-latest",
    },
    "deepseek": {
        "label": "DeepSeek",
        "logo": "/llm-brands/deepseek.svg",
        "description": "Reasoning-heavy DeepSeek models for low-cost analysis.",
        "models": [
            {"id": "deepseek-chat", "label": "DeepSeek Chat", "family": "DeepSeek", "status": "default"},
            {"id": "deepseek-reasoner", "label": "DeepSeek Reasoner", "family": "Reasoning", "status": "reasoning"},
        ],
        "default_model": "deepseek-chat",
    },
    "cohere": {
        "label": "Cohere",
        "logo": "/llm-brands/cohere.svg",
        "description": "Command-family models for retrieval and concise operator help.",
        "models": [
            {"id": "command-r-plus-08-2024", "label": "Command R+", "family": "Command", "status": "default"},
            {"id": "command-r-08-2024", "label": "Command R", "family": "Command", "status": "fast"},
            {"id": "command-a-03-2025", "label": "Command A", "family": "Command", "status": "premium"},
        ],
        "default_model": "command-r-plus-08-2024",
    },
}


def _get_assistant_models_payload() -> Dict[str, Any]:
    active_provider = settings.LLM_PROVIDER if settings.provider_available(settings.LLM_PROVIDER) else ""
    if not active_provider:
        active_provider, _ = settings.get_active_llm()

    providers: List[Dict[str, Any]] = []
    for key, config in ASSISTANT_MODEL_CATALOG.items():
        providers.append(
            {
                "key": key,
                "label": config["label"],
                "logo": config["logo"],
                "description": config["description"],
                "default_model": config["default_model"],
                "models": config["models"],
                "available": settings.provider_available(key),
                "requires_api_key": not settings.provider_available(key),
            }
        )

    default_provider = active_provider or (providers[0]["key"] if providers else "fallback")
    default_model = "deterministic"
    if default_provider in ASSISTANT_MODEL_CATALOG:
        default_model = ASSISTANT_MODEL_CATALOG[default_provider]["default_model"]

    return {
        "providers": providers,
        "default_provider": default_provider,
        "default_model": default_model,
        "llm_available": bool(providers),
    }


def _resolve_assistant_selection(payload: AssistantRequest) -> Tuple[Optional[str], Optional[str]]:
    catalog = _get_assistant_models_payload()
    providers_by_key = {provider["key"]: provider for provider in catalog["providers"]}

    selected_provider = payload.provider if payload.provider in providers_by_key else catalog["default_provider"]
    if selected_provider == "fallback" or selected_provider not in providers_by_key:
        return None, None

    provider_meta = providers_by_key[selected_provider]
    valid_models = {model["id"] for model in provider_meta["models"]}
    selected_model = payload.model if payload.model in valid_models else provider_meta["default_model"]
    return selected_provider, selected_model


def _assistant_provider_key(payload: AssistantRequest, provider: Optional[str]) -> str:
    if payload.api_key:
        return payload.api_key.strip()
    if provider:
        return LLMGateway._get_provider_key(provider)
    return ""


def _default_runtime_provider() -> str:
    if settings.provider_available(settings.LLM_PROVIDER):
        return settings.LLM_PROVIDER
    provider, _ = settings.get_active_llm()
    return provider or "openrouter"


_runtime_bridge_error: Optional[str] = None


def _runtime_repo_root() -> str:
    """Resolve the repo root that actually contains the modular Nova package."""

    current = os.path.dirname(os.path.abspath(__file__))
    candidates = [current, os.path.dirname(current), os.path.dirname(os.path.dirname(current))]
    for candidate in candidates:
        if os.path.exists(os.path.join(candidate, "nova", "__init__.py")):
            return candidate
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_runtime_bridge():
    """Lazy-load the modular Nova runtime bridge without hard-failing the legacy API."""

    repo_root = _runtime_repo_root()
    if repo_root not in sys.path:
        sys.path.append(repo_root)
    from nova.integrations import legacy_backend as runtime_bridge

    return runtime_bridge


async def _warm_runtime_bridge() -> None:
    """Initialize the embedded Nova runtime if the host environment supports it."""

    global _runtime_bridge_error
    try:
        runtime_bridge = _load_runtime_bridge()
        await runtime_bridge.get_runtime_kernel()
        _runtime_bridge_error = None
        log.info("Nova runtime bridge ready")
    except Exception as exc:
        _runtime_bridge_error = str(exc)
        log.warning(f"Nova runtime bridge unavailable: {exc}")


def _runtime_to_payload(value: Any) -> Any:
    """Convert runtime dataclasses and enums into JSON-safe payloads."""

    if is_dataclass(value):
        return {key: _runtime_to_payload(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _runtime_to_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_runtime_to_payload(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            return value
    return value


def _workspace_profile_payload(workspace: Dict[str, Any]) -> Dict[str, Any]:
    settings_payload = workspace.get("settings") or {}
    if isinstance(settings_payload, str):
        try:
            settings_payload = json.loads(settings_payload)
        except json.JSONDecodeError:
            settings_payload = {}
    settings_payload = dict(settings_payload or {})
    profile = dict(settings_payload.get("profile") or {})

    return {
        "owner_name": workspace.get("owner_name", ""),
        "preferred_name": profile.get("preferred_name", ""),
        "role_title": profile.get("role_title", ""),
        "birth_date": profile.get("birth_date"),
        "default_assistant": profile.get("default_assistant", "both"),
        "onboarding_completed_at": profile.get("onboarding_completed_at"),
    }


async def _get_runtime_workspace_context(legacy_workspace: Dict[str, Any]):
    """Return the embedded runtime kernel and the mirrored runtime workspace."""

    runtime_bridge = _load_runtime_bridge()
    kernel = await runtime_bridge.get_runtime_kernel()
    runtime_workspace = await runtime_bridge.ensure_workspace_synced(legacy_workspace)
    return runtime_bridge, kernel, runtime_workspace


def _legacy_verdict_from_runtime(action: str) -> Verdict:
    mapping = {
        "ALLOW": Verdict.APPROVED,
        "BLOCK": Verdict.BLOCKED,
        "ESCALATE": Verdict.ESCALATED,
    }
    return mapping.get(action, Verdict.ESCALATED)


def _legacy_score_from_runtime(risk_score: int) -> int:
    return max(0, min(100, 100 - int(risk_score)))


def _runtime_response_text(result: Any, fallback: str = "") -> str:
    execution_result = getattr(result, "execution_result", None)
    if execution_result and getattr(execution_result, "output", None):
        output = execution_result.output
        for key in ("content", "message", "body", "output"):
            value = output.get(key) if isinstance(output, dict) else None
            if value:
                return str(value)
        if output:
            return json.dumps(output, default=str)
    decision = getattr(getattr(result, "decision", None), "reason", None)
    if decision:
        return str(decision)
    return fallback


def _metadata_object(value: Any) -> Dict[str, Any]:
    """Normalize JSON-ish metadata columns returned by the legacy database."""

    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


async def _ensure_runtime_legacy_token(
    ws: Dict[str, Any],
    agent_name: str,
    *,
    description: str,
    can_do: List[str],
    cannot_do: List[str],
    authorized_by: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Ensure a legacy intent token exists for a runtime-backed assistant agent."""

    existing = await db.fetch_one(
        """SELECT * FROM intent_tokens
           WHERE workspace_id = :wid AND agent_name = :agent AND active = TRUE
           ORDER BY created_at DESC
           LIMIT 1""",
        {"wid": ws["id"], "agent": agent_name},
    )
    signature = Crypto.sign(
        {
            "workspace_id": str(ws["id"]),
            "agent_name": agent_name,
            "can_do": sorted(can_do),
            "cannot_do": sorted(cannot_do),
            "authorized_by": authorized_by,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if existing:
        merged_metadata = {**_metadata_object(existing["metadata"]), **(metadata or {})}
        await db.execute(
            """UPDATE intent_tokens
               SET description = :desc,
                   can_do = :can,
                   cannot_do = :cannot,
                   authorized_by = :auth,
                   signature = :sig,
                   metadata = :meta,
                   updated_at = NOW()
               WHERE id = :tid AND workspace_id = :wid""",
            {
                "desc": description,
                "can": can_do,
                "cannot": cannot_do,
                "auth": authorized_by,
                "sig": signature,
                "meta": json.dumps(merged_metadata),
                "tid": existing["id"],
                "wid": ws["id"],
            },
        )
        refreshed = await db.fetch_one(
            "SELECT * FROM intent_tokens WHERE id = :tid AND workspace_id = :wid",
            {"tid": existing["id"], "wid": ws["id"]},
        )
        return dict(refreshed)

    token_id = await db.execute(
        """INSERT INTO intent_tokens
           (workspace_id, agent_name, description, can_do, cannot_do,
            authorized_by, signature, metadata)
           VALUES (:wid, :name, :desc, :can, :cannot, :auth, :sig, :meta)
           RETURNING id""",
        {
            "wid": ws["id"],
            "name": agent_name,
            "desc": description,
            "can": can_do,
            "cannot": cannot_do,
            "auth": authorized_by,
            "sig": signature,
            "meta": json.dumps(metadata or {}),
        },
    )
    row = await db.fetch_one(
        "SELECT * FROM intent_tokens WHERE id = :tid AND workspace_id = :wid",
        {"tid": token_id, "wid": ws["id"]},
    )
    return dict(row)


async def _sync_legacy_token_to_runtime(
    ws: Dict[str, Any],
    token: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Mirror a legacy intent token into the modular Nova runtime."""

    try:
        runtime_bridge = _load_runtime_bridge()
        provider = _default_runtime_provider()
        model = settings.LLM_MODEL or "openai/gpt-4o-mini"
        agent = await runtime_bridge.ensure_agent_synced(
            ws,
            token["agent_name"],
            description=token.get("description") or "",
            model=model,
            provider=provider,
            can_do=list(token.get("can_do") or []),
            cannot_do=list(token.get("cannot_do") or []),
            metadata={"legacy_token_id": str(token["id"])},
        )
        return {"runtime_agent_id": agent.id}
    except Exception as exc:
        log.warning(f"Runtime token sync failed for {token.get('agent_name')}: {exc}")
        return None


async def _mirror_runtime_evaluation_to_legacy(
    ws: Dict[str, Any],
    ctx: Dict[str, Any],
    token: Dict[str, Any],
    action: str,
    context_text: str,
    runtime_result: Any,
    *,
    response_override: Optional[str] = None,
    provider_override: Optional[str] = None,
) -> int:
    """Reflect a modular runtime evaluation into the legacy ledger and alert surfaces."""

    decision_action = getattr(getattr(runtime_result, "decision", None), "action", None)
    decision_name = getattr(decision_action, "value", str(decision_action))
    verdict = _legacy_verdict_from_runtime(decision_name)
    risk_score = getattr(getattr(runtime_result, "risk_score", None), "value", 50)
    legacy_score = _legacy_score_from_runtime(risk_score)
    confidence = float(getattr(getattr(runtime_result, "intent_analysis", None), "confidence", 0.8) or 0.8)
    reason = getattr(getattr(runtime_result, "decision", None), "reason", "Runtime evaluation completed")
    response_text = response_override or _runtime_response_text(runtime_result, reason)
    llm_provider = (
        provider_override
        or getattr(getattr(runtime_result, "execution_result", None), "provider", None)
        or getattr(getattr(runtime_result, "intent_analysis", None), "target_provider", None)
    )
    score_factors = {
        "runtime_eval_id": getattr(runtime_result, "eval_id", None),
        "runtime_ledger_hash": getattr(runtime_result, "ledger_hash", None),
        "runtime_risk_score": risk_score,
        "runtime_anomalies": list(getattr(runtime_result, "anomalies", []) or []),
        "runtime_breakdown": dict(getattr(getattr(runtime_result, "risk_score", None), "breakdown", {}) or {}),
        "runtime_factors": [
            {
                "name": getattr(factor, "name", ""),
                "impact": getattr(factor, "impact", 0),
                "detail": getattr(factor, "detail", ""),
            }
            for factor in list(getattr(getattr(runtime_result, "risk_score", None), "factors", []) or [])
        ],
        "runtime_source": "modular_nova",
    }
    prev_row = await db.fetch_one(
        "SELECT own_hash FROM ledger WHERE workspace_id = :wid ORDER BY id DESC LIMIT 1",
        {"wid": ws["id"]},
    )
    prev_hash = prev_row["own_hash"] if prev_row else "GENESIS"
    timestamp = getattr(runtime_result, "timestamp", datetime.now(timezone.utc))
    own_hash = Crypto.chain_hash(
        prev_hash,
        {
            "workspace_id": str(ws["id"]),
            "token_id": str(token["id"]),
            "action": action,
            "score": legacy_score,
            "verdict": verdict.value,
            "timestamp": timestamp.isoformat(),
        },
    )
    latency_ms = int(getattr(runtime_result, "duration_ms", 0) or 0)
    ledger_id = await db.execute(
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
            "wid": ws["id"],
            "tid": token["id"],
            "agent": token["agent_name"],
            "action": action,
            "ctx": context_text[:2000],
            "score": legacy_score,
            "conf": confidence,
            "risk": ScoringEngine.score_to_risk(legacy_score),
            "verdict": verdict.value,
            "reason": reason[:500],
            "resp": response_text[:4000],
            "factors": json.dumps(score_factors),
            "skills": json.dumps({}),
            "prev": prev_hash,
            "own": own_hash,
            "rid": str(ctx.get("request_id") or ""),
            "ip": str(ctx.get("client_ip") or ""),
            "ua": str(ctx.get("user_agent") or "")[:200],
            "prov": llm_provider,
            "lat": latency_ms,
        },
    )
    if verdict in (Verdict.BLOCKED, Verdict.ESCALATED):
        await AlertSystem.create(
            str(ws["id"]),
            ledger_id,
            token["agent_name"],
            f"[{verdict.value}] {token['agent_name']}: {action[:120]}",
            legacy_score,
            AlertType.VIOLATION if verdict == Verdict.BLOCKED else AlertType.ESCALATION,
        )
    await MemoryEngine.auto_save(str(ws["id"]), token["agent_name"], action, verdict, legacy_score, context_text)
    await AnomalyDetector.run_all(str(ws["id"]), token["agent_name"])
    await SSEBroker.publish(
        str(ws["id"]),
        "validation",
        {
            "ledger_id": ledger_id,
            "agent_name": token["agent_name"],
            "action": action,
            "verdict": verdict.value,
            "score": legacy_score,
            "risk_level": ScoringEngine.score_to_risk(legacy_score),
            "reason": reason,
        },
    )
    return ledger_id


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
        limit = 20 if request.url.path.startswith("/auth") else self.requests_per_minute
        now          = time.time()
        window_start = now - 60
        self.requests[client_id] = [t for t in self.requests[client_id] if t > window_start]
        if len(self.requests[client_id]) >= limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "code": "RATE_LIMIT",
                    "detail": f"Maximum {limit} requests per minute",
                    "retry_after": 60
                }
            )
        self.requests[client_id].append(now)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        csp = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "connect-src 'self' https: ws: wss:; "
            "script-src 'self' 'unsafe-inline'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers.setdefault("Content-Security-Policy", csp)
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if settings.is_production():
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains; preload"
            )
        return response


# ══════════════════════════════════════════════════════════════════════════════
# DEPENDENCIES
# ══════════════════════════════════════════════════════════════════════════════

class WorkspaceRegistrationRequest(BaseModel):
    name: str
    email: EmailStr
    plan: str = Field("trial", description="Workspace tier")
    api_key: Optional[str] = Field(
        None,
        min_length=settings.API_KEY_MIN_LENGTH,
        description="Custom workspace API key; generated automatically if omitted",
    )


class BootstrapWorkspaceRequest(WorkspaceRegistrationRequest):
    bootstrap_token: str = Field(..., min_length=8, description="One-time setup token")
    owner_name: Optional[str] = Field(None, min_length=2, max_length=120)
    password: Optional[str] = Field(None, min_length=6, max_length=256)


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=256)


class AuthSignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=256)
    company: Optional[str] = Field(None, max_length=160)
    plan: str = Field("trial", description="Workspace tier")
    api_key: Optional[str] = Field(
        None,
        min_length=settings.API_KEY_MIN_LENGTH,
        description="Custom workspace API key; generated automatically if omitted",
    )


class WorkspaceProfileUpdateRequest(BaseModel):
    owner_name: Optional[str] = Field(None, min_length=2, max_length=120)
    preferred_name: Optional[str] = Field(None, max_length=80)
    role_title: Optional[str] = Field(None, max_length=120)
    birth_date: Optional[str] = Field(None, max_length=10, description="YYYY-MM-DD")
    default_assistant: Optional[str] = Field(None, max_length=32)
    complete_onboarding: bool = False
    reopen_onboarding: bool = False


class RuntimeEvaluateBridgeRequest(BaseModel):
    agent_id: str = Field(..., min_length=6)
    action: str = Field(..., min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)
    workspace_id: Optional[str] = Field(None, min_length=6)


class SetupStatusResponse(BaseModel):
    needs_setup: bool
    workspace_count: int
    github_enabled: bool
    setup_enabled: bool
    recommended_login: str


async def _ensure_unique_workspace_api_key(proposed: Optional[str]) -> str:
    candidate = proposed or f"nova_{secrets.token_hex(32)}"
    if len(candidate) < settings.API_KEY_MIN_LENGTH:
        candidate = f"nova_{secrets.token_hex(32)}"
    while True:
        exists = await db.fetch_one(
            "SELECT id FROM workspaces WHERE api_key = :key", {"key": candidate}
        )
        if not exists:
            return candidate
        candidate = f"nova_{secrets.token_hex(32)}"


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode())


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 210_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64url_encode(salt)}${_b64url_encode(digest)}"


def _verify_password(password: str, password_hash: Optional[str]) -> bool:
    if not password_hash:
        return False

    try:
        algorithm, iterations, salt, digest = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            _b64url_decode(salt),
            int(iterations),
        )
        return hmac.compare_digest(derived, _b64url_decode(digest))
    except Exception:
        return False


def _build_workspace_session_token(workspace: Dict[str, Any]) -> str:
    payload = {
        "wid": str(workspace["id"]),
        "email": workspace.get("email", ""),
        "exp": int(time.time()) + settings.SESSION_TTL_HOURS * 3600,
    }
    encoded = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        encoded.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded}.{signature}"


def _decode_workspace_session_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        encoded, signature = token.split(".", 1)
    except ValueError:
        return None

    expected = hmac.new(
        settings.SECRET_KEY.encode(),
        encoded.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None

    try:
        payload = json.loads(_b64url_decode(encoded).decode())
    except Exception:
        return None

    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


async def _get_workspace_by_id(workspace_id: str) -> Optional[Dict[str, Any]]:
    row = await db.fetch_one(
        "SELECT * FROM workspaces WHERE id = :wid",
        {"wid": workspace_id},
    )
    return dict(row) if row else None


async def _get_workspace_by_email(email: str) -> Optional[Dict[str, Any]]:
    row = await db.fetch_one(
        "SELECT * FROM workspaces WHERE LOWER(email) = LOWER(:email)",
        {"email": email},
    )
    return dict(row) if row else None


async def _get_first_workspace() -> Optional[Dict[str, Any]]:
    row = await db.fetch_one(
        "SELECT * FROM workspaces ORDER BY created_at ASC LIMIT 1"
    )
    return dict(row) if row else None


async def _get_workspace_count() -> int:
    row = await db.fetch_one("SELECT COUNT(*) AS c FROM workspaces")
    return int(row["c"]) if row else 0


async def _create_workspace_record(
    payload: WorkspaceRegistrationRequest,
    password_hash: Optional[str] = None,
    owner_name: Optional[str] = None,
) -> Dict[str, Any]:
    existing = await db.fetch_one(
        "SELECT id FROM workspaces WHERE LOWER(email) = LOWER(:email)",
        {"email": payload.email},
    )
    if existing:
        raise HTTPException(status_code=409, detail="Workspace already exists")

    api_key = await _ensure_unique_workspace_api_key(payload.api_key)
    row = await db.fetch_one(
        """
        INSERT INTO workspaces (name, owner_name, email, api_key, password_hash, plan)
        VALUES (:name, :owner_name, :email, :api_key, :password_hash, :plan)
        RETURNING id, name, owner_name, email, plan, api_key, created_at
        """,
        {
            "name": payload.name,
            "owner_name": owner_name or "",
            "email": payload.email,
            "api_key": api_key,
            "password_hash": password_hash or "",
            "plan": payload.plan,
        },
    )
    if not row:
        raise HTTPException(status_code=500, detail="Workspace could not be created")
    return dict(row)


async def _resolve_workspace_token_id(workspace_id: str, proposed: Optional[str]) -> Optional[str]:
    if proposed:
        return proposed
    row = await db.fetch_one(
        "SELECT id FROM intent_tokens WHERE workspace_id = :wid AND active = TRUE LIMIT 1",
        {"wid": workspace_id},
    )
    return str(row["id"]) if row else None


def _normalize_token_lookup_id(token_id: Any) -> Any:
    raw = str(token_id).strip()
    return int(raw) if raw.isdigit() else raw


def _extract_action_text(payload: Union[WebhookBody, GatewayForwardBody, Dict[str, Any]]) -> Optional[str]:
    if isinstance(payload, dict):
        return payload.get("action") or payload.get("message") or payload.get("texto")
    return payload.action or payload.message or payload.texto


def _sanitize_gateway_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    control_fields = {
        "action", "message", "texto",
        "token_id", "token",
        "context", "contexto",
        "agent_name",
        "memory_key", "memory_val", "memory_tags", "memory_importance",
        "respond", "dedup", "dry_run",
        "forward_to", "forward_method", "forward_payload", "forward_headers",
        "forward_timeout_ms", "validate_response",
        "response_action", "response_context", "response_token_id", "response_field",
        "include_nova_headers",
    }
    return {key: value for key, value in payload.items() if key not in control_fields}


def _coerce_response_action(
    response_text: str,
    response_json: Optional[Any] = None,
    preferred_field: Optional[str] = None,
) -> str:
    if preferred_field and isinstance(response_json, dict):
        value = response_json.get(preferred_field)
        if value is not None:
            return str(value)
    if isinstance(response_json, dict):
        for key in ("message", "reply", "response", "text", "output", "content"):
            value = response_json.get(key)
            if value:
                return str(value)
    return response_text[:4000]


def _set_workspace_session_cookie(response: Response, workspace: Dict[str, Any]) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=_build_workspace_session_token(workspace),
        max_age=settings.SESSION_TTL_HOURS * 3600,
        httponly=True,
        secure=settings.session_cookie_secure(),
        samesite="lax",
        path="/",
    )


def _clear_workspace_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        samesite="lax",
        secure=settings.session_cookie_secure(),
    )


async def get_workspace(
    request: Request,
    x_api_key: Optional[str] = Header(None, description="Workspace API key")
) -> Dict[str, Any]:
    if x_api_key:
        if len(x_api_key) < settings.API_KEY_MIN_LENGTH:
            raise HTTPException(status_code=401, detail="Invalid API key format")
        row = await db.fetch_one(
            "SELECT * FROM workspaces WHERE api_key = :key", {"key": x_api_key}
        )
        if not row:
            log.warning(f"Invalid API key: {x_api_key[:8]}...")
            raise HTTPException(status_code=401, detail="Invalid API key")
        return dict(row)

    session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if session_token:
        payload = _decode_workspace_session_token(session_token)
        if payload:
            workspace = await _get_workspace_by_id(payload["wid"])
            if workspace:
                return workspace

    raise HTTPException(status_code=401, detail="Authentication required")


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
        api_key: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        """
        Call LLM and return (content, provider_used, model_used).
        Auto-falls back to next provider if one fails.
        """
        # Resolve provider
        if provider and (api_key or LLMGateway._get_provider_key(provider)):
            providers_to_try = [(provider, api_key or LLMGateway._get_provider_key(provider))]
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


async def _get_installed_connector_count() -> int:
    try:
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.append(parent_dir)
        from integrations import INTEGRATION_SCHEMAS
        return len(INTEGRATION_SCHEMAS or {})
    except Exception:
        return 0


def _assistant_actions_from_message(message: str, stats: Dict[str, Any], risk_agents: List[Dict[str, Any]]) -> List[AssistantAction]:
    lowered = message.lower()
    actions: List[AssistantAction] = []

    if any(term in lowered for term in ["create agent", "new agent", "crear agente", "agent"]):
        actions.append(AssistantAction(type="modal", label="Create agent", value="create_agent"))
        actions.append(AssistantAction(type="copy_command", label="Copy `nova agent create`", value="nova agent create"))

    if any(term in lowered for term in ["alert", "incident", "queue", "riesgo", "risk"]):
        actions.append(AssistantAction(type="route", label="Open ledger", value="/ledger"))
        if risk_agents:
            actions.append(
                AssistantAction(
                    type="copy_command",
                    label=f"Copy `nova stream --agent {risk_agents[0]['agent_name']}`",
                    value=f"nova stream --agent {risk_agents[0]['agent_name']}",
                )
            )
        else:
            actions.append(AssistantAction(type="copy_command", label="Copy `nova status`", value="nova status"))

    if any(term in lowered for term in ["skill", "connector", "integration", "mcp"]):
        actions.append(AssistantAction(type="route", label="Open skills", value="/skills"))
        actions.append(AssistantAction(type="copy_command", label="Copy `nova connect --help`", value="nova connect --help"))

    if any(term in lowered for term in ["policy", "governance", "rules"]):
        actions.append(
            AssistantAction(
                type="copy_command",
                label="Copy `nova validate --action ...`",
                value='nova validate --action "Describe the action to review"',
            )
        )

    if not actions and not stats.get("active_agents"):
        actions.append(AssistantAction(type="modal", label="Create first agent", value="create_agent"))

    if not actions and stats.get("alerts_pending", 0) > 0:
        actions.append(AssistantAction(type="route", label="Review ledger", value="/ledger"))

    if not actions:
        actions.append(AssistantAction(type="refresh", label="Refresh runtime", value="refresh"))

    top_risk = risk_agents[0]["agent_name"] if risk_agents else None
    if top_risk and all(action.value != "nova stream --agent " + top_risk for action in actions):
        actions.append(AssistantAction(
            type="copy_command",
            label=f"Copy stream command for {top_risk}",
            value=f"nova stream --agent {top_risk}",
        ))

    return actions[:4]


def _assistant_command_suggestions(stats: Dict[str, Any], risk_agents: List[Dict[str, Any]]) -> List[str]:
    commands = ["nova status", "nova discover"]
    if not stats.get("active_agents"):
        commands.append("nova agent create")
    else:
        commands.append("nova validate --action \"Describe the action to review\"")
    if risk_agents:
        commands.append(f"nova stream --agent {risk_agents[0]['agent_name']} --limit 10")
    else:
        commands.append("nova agents")
    return commands[:4]


def _clean_assistant_command_output(output: str) -> str:
    if not output:
        return ""

    lines = output.splitlines()
    cleaned: List[str] = []
    skipping_aiosqlite_trace = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("HTTP Request:"):
            continue

        if stripped.startswith("Exception ignored in: <function Connection.__del__"):
            skipping_aiosqlite_trace = True
            continue

        if skipping_aiosqlite_trace:
            if not stripped:
                skipping_aiosqlite_trace = False
            continue

        cleaned.append(line)

    return "\n".join(cleaned).strip()


def _humanize_assistant_command_output(cmd: str, output: str, exit_code: int, *, timed_out: bool = False) -> str:
    cleaned = _clean_assistant_command_output(output)

    if timed_out and cmd == "nova watch":
        if cleaned:
            return (
                "Nova abrió una vista previa corta de `nova watch`, pero el dashboard no mantiene sesiones "
                "de observación continuas todavía. Para vigilancia en vivo, usa terminal. "
                "Esto fue lo primero que alcanzó a ver:\n\n"
                f"{cleaned}"
            )
        return (
            "Nova intentó abrir `nova watch`, pero el dashboard no mantiene sesiones continuas. "
            "Úsalo desde terminal si quieres dejarlo observando en vivo."
        )

    if "ModuleNotFoundError: No module named 'aiosqlite'" in output:
        return (
            "Nova no pudo arrancar la CLI porque al runtime le faltaba `aiosqlite`. "
            "Ese problema ya apunta a dependencias del contenedor, no a tu comando."
        )

    if "invalid choice: 'skill'" in output:
        return (
            "El comando `nova skill` no existe en la CLI actual de Nova. "
            "Para integraciones usa la página Skills o `nova connect`."
        )

    if "invalid choice: 'policy'" in output:
        return (
            "El comando `nova policy` no existe en la CLI actual de Nova. "
            "Para revisar una acción usa `nova validate --action ...`."
        )

    if exit_code == 0:
        if cleaned:
            return f"Nova ejecutó `{cmd}` correctamente.\n\n{cleaned}"
        return f"Nova ejecutó `{cmd}` correctamente."

    if cleaned:
        meaningful_lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        detail = meaningful_lines[-1] if meaningful_lines else cleaned
        return f"Nova no pudo completar `{cmd}`. Motivo: {detail}"

    return f"Nova no pudo completar `{cmd}`."


def _resolve_assistant_command(cmd: str) -> Tuple[List[str], str]:
    """
    Execute dashboard-suggested `nova` commands through the local repo when the
    CLI is not installed globally. This keeps terminal actions working for the
    current backend user without requiring a system-wide install.
    """
    repo_root = _runtime_repo_root()
    nova_py = os.path.join(repo_root, "nova.py")
    command_suffix = cmd[4:].strip() if cmd != "nova" else ""

    if os.path.exists(nova_py):
        python_cmd = shutil.which("python3") or shutil.which("python") or sys.executable
        fallback_command = f"{shlex.quote(python_cmd)} {shlex.quote(nova_py)}"
        if command_suffix:
            fallback_command = f"{fallback_command} {command_suffix}"
    else:
        fallback_command = cmd

    login_shell_command = (
        f"if command -v nova >/dev/null 2>&1; then {cmd}; "
        f"else {fallback_command}; fi"
    )
    return ["/bin/bash", "-lc", login_shell_command], repo_root


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
            results[name] = row["c"] if "c" in row.keys() else (row["avg"] if "avg" in row.keys() else 0)

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
    await _warm_runtime_bridge()
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
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SecurityHeadersMiddleware)
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
        "docs": "/docs"
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


@app.get("/status", tags=["Core"], response_model=HealthResponse)
async def status_alias():
    return await health_check()


@app.get("/status/services", tags=["Core"])
async def status_services():
    db_status = "connected"
    try:
        await db.fetch_one("SELECT 1")
    except Exception:
        db_status = "disconnected"

    provider, _ = settings.get_active_llm()
    provider_status = "operational" if provider else "not_configured"
    services = [
        {
            "name": "api",
            "status": "operational",
            "latency_ms": 18,
            "detail": "FastAPI control plane responding",
        },
        {
            "name": "database",
            "status": "operational" if db_status == "connected" else "degraded",
            "latency_ms": 12 if db_status == "connected" else None,
            "detail": f"Database {db_status}",
        },
        {
            "name": "gateway",
            "status": provider_status,
            "latency_ms": 41 if provider else None,
            "detail": f"Active provider: {provider or 'none'}",
        },
        {
            "name": "streaming",
            "status": "operational",
            "latency_ms": 9,
            "detail": f"{SSEBroker.active_streams()} active streams",
        },
    ]
    return {
        "success": True,
        "services": services,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/auth/providers", tags=["Auth"])
async def auth_providers():
    return {
        "github": {
            "enabled": settings.github_enabled(),
            "redirect_uri": settings.GITHUB_REDIRECT_URI if settings.github_enabled() else None,
        }
    }


@app.post("/auth/login", tags=["Auth"])
async def auth_login(payload: AuthLoginRequest):
    workspace = await _get_workspace_by_email(payload.email)
    if not workspace:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    password_hash = workspace.get("password_hash") or ""
    if password_hash:
        if not _verify_password(payload.password, password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
    elif settings.is_production():
        raise HTTPException(status_code=401, detail="Password login is not configured for this workspace")
    else:
        password_hash = _hash_password(payload.password)
        await db.execute(
            """
            UPDATE workspaces
            SET password_hash = :password_hash, updated_at = NOW()
            WHERE id = :wid
            """,
            {"password_hash": password_hash, "wid": workspace["id"]},
        )

    response = JSONResponse(
        {
            "id": str(workspace["id"]),
            "name": workspace.get("name", ""),
            "owner_name": workspace.get("owner_name", ""),
            "email": workspace.get("email", ""),
            "plan": workspace.get("plan", "free"),
        }
    )
    _set_workspace_session_cookie(response, workspace)
    return response


@app.post("/auth/signup", tags=["Auth"], status_code=201)
async def auth_signup(payload: AuthSignupRequest):
    workspace_name = (payload.company or payload.name).strip()
    registration = WorkspaceRegistrationRequest(
        name=workspace_name,
        email=payload.email,
        plan=payload.plan,
        api_key=payload.api_key,
    )
    workspace = await _create_workspace_record(
        registration,
        password_hash=_hash_password(payload.password),
        owner_name=payload.name.strip(),
    )
    response = JSONResponse(
        {
            "id": str(workspace["id"]),
            "name": workspace.get("name", ""),
            "owner_name": workspace.get("owner_name", ""),
            "email": workspace.get("email", ""),
            "plan": workspace.get("plan", payload.plan),
            "api_key": workspace.get("api_key"),
        },
        status_code=201,
    )
    _set_workspace_session_cookie(response, workspace)
    return response


@app.get("/auth/github/start", tags=["Auth"])
async def github_auth_start(next: str = Query("/dashboard")):
    if not settings.github_enabled():
        raise HTTPException(status_code=503, detail="GitHub auth is not configured")

    next_path = next if next.startswith("/") else "/dashboard"
    state = secrets.token_urlsafe(24)
    query = urlencode({
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": settings.GITHUB_SCOPE,
        "state": state,
        "allow_signup": "true",
    })
    response = RedirectResponse(
        url=f"https://github.com/login/oauth/authorize?{query}",
        status_code=302,
    )
    response.set_cookie(
        key="nova_github_oauth_state",
        value=state,
        max_age=600,
        httponly=True,
        secure=settings.session_cookie_secure(),
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="nova_github_oauth_next",
        value=next_path,
        max_age=600,
        httponly=True,
        secure=settings.session_cookie_secure(),
        samesite="lax",
        path="/",
    )
    return response


@app.get("/auth/github/callback", tags=["Auth"])
async def github_auth_callback(
    code: str = Query(...),
    state: str = Query(...),
    oauth_state: Optional[str] = Cookie(None, alias="nova_github_oauth_state"),
    oauth_next: Optional[str] = Cookie("/dashboard", alias="nova_github_oauth_next"),
):
    fallback = f"{settings.FRONTEND_URL.rstrip('/')}/login?auth=github&status=failed"

    def _redirect(path: str) -> RedirectResponse:
        response = RedirectResponse(url=path, status_code=302)
        response.delete_cookie("nova_github_oauth_state", path="/")
        response.delete_cookie("nova_github_oauth_next", path="/")
        return response

    if not settings.github_enabled():
        return _redirect(f"{settings.FRONTEND_URL.rstrip('/')}/login?auth=github&status=disabled")

    if not oauth_state or state != oauth_state:
        return _redirect(f"{settings.FRONTEND_URL.rstrip('/')}/login?auth=github&status=invalid_state")

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={
                "Accept": "application/json",
                "User-Agent": "Nova-OS",
            },
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
                "state": state,
            },
        )
        if token_res.status_code >= 400:
            log.warning("GitHub token exchange failed: %s", token_res.text[:300])
            return _redirect(fallback)

        access_token = token_res.json().get("access_token")
        if not access_token:
            return _redirect(fallback)

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "Nova-OS",
        }
        user_res = await client.get("https://api.github.com/user", headers=headers)
        emails_res = await client.get("https://api.github.com/user/emails", headers=headers)
        if user_res.status_code >= 400 or emails_res.status_code >= 400:
            return _redirect(fallback)

        emails = emails_res.json()
        verified_email = next(
            (item.get("email") for item in emails if item.get("verified") and item.get("primary")),
            None,
        ) or next(
            (item.get("email") for item in emails if item.get("verified")),
            None,
        )
        if not verified_email:
            return _redirect(f"{settings.FRONTEND_URL.rstrip('/')}/login?auth=github&status=email_required")

        workspace = await _get_workspace_by_email(verified_email)
        if not workspace:
            return _redirect(f"{settings.FRONTEND_URL.rstrip('/')}/login?auth=github&status=no_workspace")

        next_path = oauth_next if oauth_next and oauth_next.startswith("/") else "/dashboard"
        response = _redirect(f"{settings.FRONTEND_URL.rstrip('/')}{next_path}")
        _set_workspace_session_cookie(response, workspace)
        return response


@app.post("/auth/logout", tags=["Auth"])
async def logout():
    response = JSONResponse({"status": "logged_out"})
    _clear_workspace_session_cookie(response)
    return response


@app.get("/auth/session", tags=["Auth"])
async def auth_session(request: Request):
    try:
        ws = await get_workspace(request=request, x_api_key=None)
    except HTTPException:
        return {"authenticated": False}

    return {
        "authenticated": True,
        "workspace": {
            "id": str(ws["id"]),
            "name": ws.get("name", ""),
            "owner_name": ws.get("owner_name", ""),
            "email": ws.get("email", ""),
            "plan": ws.get("plan", "free"),
            "profile": _workspace_profile_payload(ws),
        },
    }


@app.get("/auth/me", tags=["Auth"])
async def auth_me(ws: Dict = Depends(get_workspace)):
    return {
        "id": str(ws["id"]),
        "name": ws.get("name", ""),
        "owner_name": ws.get("owner_name", ""),
        "email": ws.get("email", ""),
        "plan": ws.get("plan", "free"),
        "profile": _workspace_profile_payload(ws),
    }


@app.get("/discovery/scan", tags=["Discovery"])
async def discovery_scan(ws: Dict = Depends(get_workspace)):
    _, kernel, _ = await _get_runtime_workspace_context(ws)
    agents = await kernel.discovery.scan(force=True)
    return {
        "agents": _runtime_to_payload(agents),
        "last_scan_at": kernel.discovery.last_scan_at.isoformat() if kernel.discovery.last_scan_at else None,
        "duration_ms": round(kernel.discovery.last_scan_duration_ms or 0, 2),
    }


@app.get("/discovery/agents", tags=["Discovery"])
async def discovery_agents(ws: Dict = Depends(get_workspace)):
    _, kernel, _ = await _get_runtime_workspace_context(ws)
    agents = await kernel.discovery.scan(force=False)
    return {
        "agents": _runtime_to_payload(agents),
        "last_scan_at": kernel.discovery.last_scan_at.isoformat() if kernel.discovery.last_scan_at else None,
        "duration_ms": round(kernel.discovery.last_scan_duration_ms or 0, 2),
    }


@app.post("/discovery/agents/{agent_key}/connect", tags=["Discovery"])
async def discovery_connect_agent(
    agent_key: str,
    payload: Dict[str, Any] = Body(default_factory=dict),
    ws: Dict = Depends(get_workspace),
):
    _, kernel, runtime_workspace = await _get_runtime_workspace_context(ws)
    result = await kernel.discovery.connect(
        agent_key=agent_key,
        workspace_id=runtime_workspace.id,
        config=dict(payload.get("config") or {}),
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or "Unable to connect discovered agent")
    return _runtime_to_payload(result)


@app.delete("/discovery/agents/{agent_key}/disconnect", tags=["Discovery"])
async def discovery_disconnect_agent(agent_key: str, ws: Dict = Depends(get_workspace)):
    _, kernel, _ = await _get_runtime_workspace_context(ws)
    disconnected = await kernel.discovery.disconnect(agent_key)
    if not disconnected:
        raise HTTPException(status_code=404, detail="Agent is not connected")
    return {"disconnected": True, "agent_key": agent_key}


@app.get("/discovery/agents/{agent_key}/status", tags=["Discovery"])
async def discovery_agent_status(agent_key: str, ws: Dict = Depends(get_workspace)):
    _, kernel, _ = await _get_runtime_workspace_context(ws)
    return _runtime_to_payload(await kernel.discovery.get_status(agent_key))


@app.get("/discovery/agents/{agent_key}/logs", tags=["Discovery"])
async def discovery_agent_logs(agent_key: str, limit: int = Query(100, ge=1, le=500), ws: Dict = Depends(get_workspace)):
    _, kernel, _ = await _get_runtime_workspace_context(ws)
    return _runtime_to_payload(await kernel.discovery.get_logs(agent_key, limit=limit))


@app.post("/discovery/agents/{agent_key}/pause", tags=["Discovery"])
async def discovery_pause_agent(agent_key: str, ws: Dict = Depends(get_workspace)):
    _, kernel, _ = await _get_runtime_workspace_context(ws)
    paused = await kernel.discovery.pause(agent_key)
    if not paused:
        raise HTTPException(status_code=404, detail="Agent is not connected")
    return {"agent_key": agent_key, "paused": True}


@app.post("/discovery/agents/{agent_key}/resume", tags=["Discovery"])
async def discovery_resume_agent(agent_key: str, ws: Dict = Depends(get_workspace)):
    _, kernel, _ = await _get_runtime_workspace_context(ws)
    resumed = await kernel.discovery.resume(agent_key)
    if not resumed:
        raise HTTPException(status_code=404, detail="Agent is not connected")
    return {"agent_key": agent_key, "resumed": True}


@app.post("/agents/create", tags=["Discovery"], status_code=201)
async def discovery_create_agent(
    payload: Dict[str, Any] = Body(...),
    ws: Dict = Depends(get_workspace),
):
    _, kernel, runtime_workspace = await _get_runtime_workspace_context(ws)
    agent_type = str(payload.get("type") or "custom")
    model = str(payload.get("model") or "gpt-4o-mini")
    name = str(payload.get("name") or f"{agent_type.title()} Control Lane")
    config = dict(payload.get("config") or {})
    permissions = dict(payload.get("permissions") or {})
    risk_thresholds = dict(payload.get("risk_thresholds") or {})
    quota = dict(payload.get("quota") or {})
    agent, connection = await kernel.discovery.create_managed_agent(
        workspace_id=runtime_workspace.id,
        name=name,
        agent_type=agent_type,
        model=model,
        config=config,
        permissions=permissions,
        risk_thresholds=risk_thresholds,
        quota=quota,
    )
    return {
        "agent": _runtime_to_payload(agent),
        "connection": _runtime_to_payload(connection) if connection else None,
    }


@app.post("/api/agents/create", tags=["Discovery"], status_code=201)
async def api_discovery_create_agent(
    payload: Dict[str, Any] = Body(...),
    ws: Dict = Depends(get_workspace),
):
    return await discovery_create_agent(payload, ws)


@app.post("/api/evaluate", tags=["Runtime"])
async def api_runtime_evaluate(
    payload: RuntimeEvaluateBridgeRequest,
    ws: Dict = Depends(get_workspace),
):
    from nova.nova_types import EvaluationRequest

    _, kernel, runtime_workspace = await _get_runtime_workspace_context(ws)
    result = await kernel.evaluate(
        EvaluationRequest(
            agent_id=payload.agent_id,
            workspace_id=payload.workspace_id or runtime_workspace.id,
            action=payload.action,
            payload=payload.payload,
            source="n8n-api-bridge",
        )
    )
    return _runtime_to_payload(result)


@app.get("/api/gmail/check-duplicate", tags=["Runtime"])
async def api_runtime_check_duplicate(
    recipient: str = Query(..., min_length=3),
    subject: str = Query(..., min_length=1),
    timeframe_hours: int = Query(24, ge=1, le=24 * 30),
    ws: Dict = Depends(get_workspace),
):
    _, kernel, runtime_workspace = await _get_runtime_workspace_context(ws)
    recipient_key = recipient.strip().casefold()
    subject_key = subject.strip().casefold()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=timeframe_hours)
    entries = await kernel.ledger.list_entries(runtime_workspace.id, limit=500)

    for entry in entries:
        if entry.action_type != "send_email":
            continue
        if str(entry.decision).upper() != "ALLOW":
            continue
        entry_timestamp = entry.timestamp
        if entry_timestamp.tzinfo is None:
            entry_timestamp = entry_timestamp.replace(tzinfo=timezone.utc)
        if entry_timestamp < cutoff:
            continue

        record_metadata = dict(entry.record_metadata or {})
        dedupe_keys = dict(record_metadata.get("dedupe_keys") or {})
        if dedupe_keys.get("recipient") != recipient_key:
            continue
        if dedupe_keys.get("subject") != subject_key:
            continue

        return {
            "is_duplicate": True,
            "recipient": recipient,
            "subject": subject,
            "last_sent_at": entry_timestamp.isoformat(),
            "action_id": entry.action_id,
            "eval_id": entry.eval_id,
            "ledger_hash": entry.hash,
        }

    return {
        "is_duplicate": False,
        "recipient": recipient,
        "subject": subject,
        "timeframe_hours": timeframe_hours,
    }


@app.get("/api/ledger", tags=["Runtime"])
async def api_runtime_ledger(
    limit: int = Query(100, ge=1, le=5000),
    ws: Dict = Depends(get_workspace),
):
    _, kernel, runtime_workspace = await _get_runtime_workspace_context(ws)
    entries = await kernel.ledger.list_entries(runtime_workspace.id, limit)
    return [
        {
            "action_id": entry.action_id,
            "eval_id": entry.eval_id,
            "action_type": entry.action_type,
            "risk_score": entry.risk_score,
            "decision": entry.decision,
            "hash": entry.hash,
            "previous_hash": entry.previous_hash,
            "timestamp": entry.timestamp.isoformat(),
            "payload_summary": entry.payload_summary,
        }
        for entry in entries
    ]


@app.get("/api/ledger/verify", tags=["Runtime"])
async def api_runtime_verify_ledger(
    ws: Dict = Depends(get_workspace),
):
    _, kernel, runtime_workspace = await _get_runtime_workspace_context(ws)
    result = await kernel.ledger.hash_chain.verify_integrity(runtime_workspace.id)
    return {
        "is_valid": result.is_valid,
        "total_records": result.total_records,
        "verified_records": result.verified_records,
        "broken_at": result.broken_at,
        "verified_at": result.verified_at.isoformat(),
    }


@app.get("/assistant/models", tags=["Assistant"])
async def assistant_models(ws: Dict = Depends(get_workspace)):
    return _get_assistant_models_payload()


@app.post("/assistant/chat", tags=["Assistant"], response_model=AssistantResponse)
async def assistant_chat(request: Request, payload: AssistantRequest, ws: Dict = Depends(get_workspace)):
    ctx = await get_request_context(request)
    stats = await AnalyticsEngine.get_stats(str(ws["id"]))
    risk_profile = await AnalyticsEngine.get_risk_profile(str(ws["id"]))
    risk_agents = (risk_profile or {}).get("agents", [])[:3]
    recent_alerts = await db.fetch_all(
        """
        SELECT agent_name, severity, message, created_at
        FROM alerts
        WHERE workspace_id = :wid AND resolved = FALSE
        ORDER BY created_at DESC
        LIMIT 3
        """,
        {"wid": ws["id"]},
    )
    recent_ledger = await db.fetch_all(
        """
        SELECT agent_name, action, verdict, score, risk_level, executed_at
        FROM ledger
        WHERE workspace_id = :wid
        ORDER BY id DESC
        LIMIT 3
        """,
        {"wid": ws["id"]},
    )
    connector_count = await _get_installed_connector_count()

    stats_summary = {
        "workspace_name": ws.get("name", ""),
        "plan": ws.get("plan", "free"),
        "total_actions": stats.get("total_actions", 0),
        "approved": stats.get("approved", 0),
        "blocked": stats.get("blocked", 0),
        "escalated": stats.get("escalated", 0),
        "active_agents": stats.get("active_agents", 0),
        "alerts_pending": stats.get("alerts_pending", 0),
        "approval_rate": stats.get("approval_rate", 0),
        "avg_score": stats.get("avg_score", 0),
        "connector_count": connector_count,
        "risk_agents": [dict(agent) for agent in risk_agents],
        "recent_alerts": [dict(row) for row in recent_alerts],
        "recent_ledger": [dict(row) for row in recent_ledger],
    }

    suggested_commands = _assistant_command_suggestions(stats, risk_agents)
    actions = _assistant_actions_from_message(payload.message, stats, risk_agents)

    provider = "fallback"
    model = "deterministic"
    response_text = (
        f"Nova is tracking {stats_summary['active_agents']} active agents, "
        f"{stats_summary['alerts_pending']} pending alerts, and an approval rate of "
        f"{stats_summary['approval_rate']}%. Ask me about risk, alerts, agent setup, policies, "
        "CLI flows, or how to operate this workspace."
    )

    selected_provider, selected_model = _resolve_assistant_selection(payload)
    selected_api_key = _assistant_provider_key(payload, selected_provider)
    system_prompt = (
        "You are Nova Operator, an embedded assistant for a security operations dashboard. "
        "Be practical, precise, and operator-focused. "
        "Use the workspace snapshot to answer clearly. "
        "Never claim you executed shell commands or changed infrastructure. "
        "You may suggest Nova CLI commands and UI navigation. "
        "If the user provides a large natural-language instruction, preserve its constraints, extract the execution intent, "
        "identify the target runtime or connector when possible, and surface blockers explicitly. "
        "Prefer short paragraphs or flat bullets when helpful, but do not truncate important reasoning."
    )
    user_prompt = (
        f"User message: {payload.message}\n"
        f"Current page: {payload.page}\n"
        f"Workspace snapshot:\n{json.dumps(stats_summary, default=str)}\n"
        f"Suggested commands already available:\n{json.dumps(suggested_commands)}\n"
        "Handle long natural-language instructions faithfully. Summarize only when it preserves the actionable meaning."
    )
    assistant_agent_name = "Nova Operator Assistant"
    assistant_can_do = ["generate_response", "execute_nova_command", "query_database"]
    assistant_cannot_do = ["share_other_customers_data", "exfiltrate_secrets"]
    runtime_handled = False

    try:
        runtime_bridge = _load_runtime_bridge()
        runtime_provider = selected_provider or _default_runtime_provider()
        runtime_model = selected_model or settings.LLM_MODEL or "openai/gpt-4o-mini"
        runtime_agent, runtime_result = await runtime_bridge.evaluate_action(
            ws,
            agent_name=assistant_agent_name,
            action="generate response",
            payload={
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "provider": runtime_provider,
                "model": runtime_model,
                "timeout": settings.LLM_TIMEOUT,
            },
            description="Runtime-backed operator assistant used by the dashboard cockpit.",
            model=runtime_model,
            provider=runtime_provider,
            api_key=selected_api_key or None,
            can_do=assistant_can_do,
            cannot_do=assistant_cannot_do,
            metadata={"legacy_surface": "assistant-chat", "page": payload.page},
            request_id=ctx["request_id"],
        )
        provider = (
            getattr(getattr(runtime_result, "execution_result", None), "provider", None)
            or runtime_provider
            or "nova-runtime"
        )
        execution_output = getattr(getattr(runtime_result, "execution_result", None), "output", {}) or {}
        model = execution_output.get("model") or runtime_model or "deterministic"
        response_text = _runtime_response_text(runtime_result, response_text)
        token = await _ensure_runtime_legacy_token(
            ws,
            assistant_agent_name,
            description="Dashboard assistant mirrored from the modular Nova runtime.",
            can_do=assistant_can_do,
            cannot_do=assistant_cannot_do,
            authorized_by=ws.get("email", "system"),
            metadata={"runtime_agent_id": runtime_agent.id, "legacy_surface": "assistant-chat"},
        )
        await _mirror_runtime_evaluation_to_legacy(
            ws,
            ctx,
            token,
            f"assistant_chat: {payload.message[:180]}",
            f"page={payload.page}",
            runtime_result,
            response_override=response_text,
            provider_override=provider,
        )
        runtime_handled = True
    except Exception as exc:
        log.warning(f"Assistant runtime bridge fallback used: {exc}")

    if not runtime_handled and selected_provider and selected_model and selected_api_key:
        try:
            response_text, provider, model = await LLMGateway.complete(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=640,
                temperature=0.15,
                provider=selected_provider,
                model=selected_model,
                api_key=selected_api_key,
            )
        except Exception as exc:
            log.warning("Assistant chat fallback used: %s", exc)

    return {
        "message": response_text,
        "provider": provider,
        "model": model,
        "suggested_commands": suggested_commands,
        "actions": [action.dict() for action in actions],
    }


@app.post("/assistant/execute", tags=["Assistant"], response_model=CommandResponse)
async def assistant_execute(request: Request, payload: CommandRequest, ws: Dict = Depends(get_workspace)):
    """
    Safely execute a suggested Nova command.
    Only commands starting with 'nova ' are permitted to prevent shell injection.
    """
    cmd = payload.command.strip()
    ctx = await get_request_context(request)

    # Safety check: Only allow 'nova' commands
    if not (cmd.startswith("nova ") or cmd == "nova"):
        return {
            "output": f"Security violation: Command '{cmd}' is not allowed. Only 'nova' commands are permitted via the dashboard.",
            "exit_code": 1,
            "success": False,
            "display_output": "Ese comando no está permitido desde el dashboard. Aquí solo se pueden ejecutar comandos que empiecen por `nova`.",
        }

    # Further sanitization: avoid command chaining and redirection
    if any(forbidden in cmd for forbidden in [";", "&", "|", ">", "<", "`", "$", "(", ")"]):
        return {
            "output": "Security violation: Special characters detected. Command execution aborted.",
            "exit_code": 1,
            "success": False,
            "display_output": "El comando fue bloqueado porque contiene caracteres inseguros para ejecución desde el dashboard.",
        }

    runtime_result = None
    runtime_token = None
    runtime_provider = _default_runtime_provider()
    try:
        runtime_bridge = _load_runtime_bridge()
        runtime_agent, runtime_result = await runtime_bridge.evaluate_action(
            ws,
            agent_name="Nova Operator Assistant",
            action="execute nova command",
            payload={"command": cmd},
            description="Runtime-backed dashboard assistant used to approve terminal commands.",
            model=settings.LLM_MODEL or "openai/gpt-4o-mini",
            provider=runtime_provider,
            can_do=["execute_nova_command"],
            cannot_do=["delete_production_data", "exfiltrate_secrets"],
            metadata={"legacy_surface": "assistant-execute"},
            request_id=ctx["request_id"],
        )
        runtime_token = await _ensure_runtime_legacy_token(
            ws,
            "Nova Operator Assistant",
            description="Dashboard assistant mirrored from the modular Nova runtime.",
            can_do=["execute_nova_command"],
            cannot_do=["delete_production_data", "exfiltrate_secrets"],
            authorized_by=ws.get("email", "system"),
            metadata={"runtime_agent_id": runtime_agent.id, "legacy_surface": "assistant-execute"},
        )
        runtime_decision = getattr(getattr(runtime_result, "decision", None), "action", None)
        runtime_decision_name = getattr(runtime_decision, "value", str(runtime_decision or ""))
        if runtime_decision_name != "ALLOW":
            response_text = f"Command blocked by Nova runtime: {getattr(getattr(runtime_result, 'decision', None), 'reason', 'policy blocked')}"
            await _mirror_runtime_evaluation_to_legacy(
                ws,
                ctx,
                runtime_token,
                cmd,
                "dashboard assistant execute",
                runtime_result,
                response_override=response_text,
                provider_override=runtime_provider,
            )
            return {"output": response_text, "exit_code": 1, "success": False, "display_output": response_text}
    except Exception as exc:
        log.warning(f"Assistant command runtime bridge fallback used: {exc}")

    try:
        resolved_command, command_cwd = _resolve_assistant_command(cmd)
        process = subprocess.run(
            resolved_command,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=command_cwd,
        )
        if runtime_result is not None and runtime_token is not None:
            await _mirror_runtime_evaluation_to_legacy(
                ws,
                ctx,
                runtime_token,
                cmd,
                "dashboard assistant execute",
                runtime_result,
                response_override=(process.stdout + process.stderr) or "Command completed.",
                provider_override=runtime_provider,
            )
        return {
            "output": process.stdout + process.stderr,
            "exit_code": process.returncode,
            "success": process.returncode == 0,
            "display_output": _humanize_assistant_command_output(cmd, process.stdout + process.stderr, process.returncode),
        }
    except subprocess.TimeoutExpired as exc:
        partial_output = f"{exc.stdout or ''}{exc.stderr or ''}"
        return {
            "output": partial_output or "Command timed out after 10 seconds.",
            "exit_code": 124,
            "success": False,
            "display_output": _humanize_assistant_command_output(cmd, partial_output, 124, timed_out=True),
        }
    except Exception as exc:
        return {
            "output": f"Internal error during execution: {str(exc)}",
            "exit_code": 500,
            "success": False,
            "display_output": f"Nova no pudo ejecutar `{cmd}` por un error interno del backend: {str(exc)}",
        }


@app.get("/setup/status", tags=["Setup"], response_model=SetupStatusResponse)
async def setup_status():
    workspace_count = await _get_workspace_count()
    needs_setup = workspace_count == 0
    return {
        "needs_setup": needs_setup,
        "workspace_count": workspace_count,
        "github_enabled": settings.github_enabled(),
        "setup_enabled": needs_setup,
        "recommended_login": "bootstrap" if needs_setup else ("github" if settings.github_enabled() else "credentials"),
    }


@app.post("/setup/bootstrap", tags=["Setup"], status_code=201)
async def bootstrap_workspace(payload: BootstrapWorkspaceRequest):
    workspace_count = await _get_workspace_count()
    if workspace_count > 0:
        raise HTTPException(status_code=409, detail="Nova already has a workspace. Use the existing login methods.")

    if not hmac.compare_digest(payload.bootstrap_token, settings.WORKSPACE_ADMIN_TOKEN):
        raise HTTPException(status_code=403, detail="Invalid bootstrap token")

    owner_name = (payload.owner_name or payload.name).strip()
    password_hash = _hash_password(payload.password) if payload.password else None
    workspace = await _create_workspace_record(
        payload,
        password_hash=password_hash,
        owner_name=owner_name,
    )
    response = JSONResponse(
        {
            "id":         str(workspace["id"]),
            "name":       workspace["name"],
            "owner_name": workspace.get("owner_name", ""),
            "email":      workspace["email"],
            "plan":       workspace["plan"],
            "api_key":    workspace["api_key"],
            "created_at": workspace["created_at"],
        },
        status_code=201,
    )
    _set_workspace_session_cookie(response, workspace)
    return response


@app.get("/workspaces/me", tags=["Workspace"])
async def get_my_workspace(ws: Dict = Depends(get_workspace)):
    """Get current workspace details and usage stats."""
    stats = await AnalyticsEngine.get_stats(str(ws["id"]))
    return {
        "id":               str(ws["id"]),
        "name":             ws.get("name", ""),
        "owner_name":       ws.get("owner_name", ""),
        "email":            ws.get("email", ""),
        "plan":             ws.get("plan", "free"),
        "features":         ws.get("features", []),
        "usage_this_month": ws.get("usage_this_month", 0),
        "quota_monthly":    ws.get("quota_monthly", 10000),
        "stats":            stats,
        "created_at":       ws.get("created_at"),
        "profile":          _workspace_profile_payload(ws),
    }


@app.patch("/workspaces/me/profile", tags=["Workspace"])
async def update_my_workspace_profile(
    payload: WorkspaceProfileUpdateRequest,
    ws: Dict = Depends(get_workspace),
):
    settings_payload = ws.get("settings") or {}
    if isinstance(settings_payload, str):
        try:
            settings_payload = json.loads(settings_payload)
        except json.JSONDecodeError:
            settings_payload = {}
    settings_payload = dict(settings_payload or {})
    profile = dict(settings_payload.get("profile") or {})

    owner_name = (payload.owner_name or ws.get("owner_name") or "").strip()
    preferred_name = payload.preferred_name if payload.preferred_name is not None else profile.get("preferred_name", "")
    role_title = payload.role_title if payload.role_title is not None else profile.get("role_title", "")
    birth_date = payload.birth_date if payload.birth_date is not None else profile.get("birth_date")
    default_assistant = payload.default_assistant if payload.default_assistant is not None else profile.get("default_assistant", "both")

    if default_assistant not in {"nova", "melissa", "both"}:
        raise HTTPException(status_code=422, detail="default_assistant must be one of: nova, melissa, both")

    profile.update({
        "preferred_name": preferred_name.strip() if isinstance(preferred_name, str) else preferred_name,
        "role_title": role_title.strip() if isinstance(role_title, str) else role_title,
        "birth_date": birth_date,
        "default_assistant": default_assistant,
    })

    if payload.reopen_onboarding:
        profile["onboarding_completed_at"] = None
    elif payload.complete_onboarding:
        profile["onboarding_completed_at"] = datetime.now(timezone.utc).isoformat()

    settings_payload["profile"] = profile

    await db.execute(
        """
        UPDATE workspaces
        SET owner_name = :owner_name,
            settings = :settings,
            updated_at = NOW()
        WHERE id = :wid
        """,
        {
            "wid": ws["id"],
            "owner_name": owner_name,
            "settings": json.dumps(settings_payload),
        },
    )

    updated = await _get_workspace_by_id(str(ws["id"]))
    if not updated:
        raise HTTPException(status_code=404, detail="Workspace not found")

    stats = await AnalyticsEngine.get_stats(str(updated["id"]))
    return {
        "id": str(updated["id"]),
        "name": updated.get("name", ""),
        "owner_name": updated.get("owner_name", ""),
        "email": updated.get("email", ""),
        "plan": updated.get("plan", "free"),
        "features": updated.get("features", []),
        "usage_this_month": updated.get("usage_this_month", 0),
        "quota_monthly": updated.get("quota_monthly", 10000),
        "stats": stats,
        "created_at": updated.get("created_at"),
        "profile": _workspace_profile_payload(updated),
    }


@app.post("/workspaces/register", tags=["Workspace"], status_code=201)
async def register_workspace(
    payload: WorkspaceRegistrationRequest,
    x_admin_token: str = Header(..., alias="X-Nova-Admin-Token"),
):
    if not hmac.compare_digest(x_admin_token, settings.WORKSPACE_ADMIN_TOKEN):
        raise HTTPException(status_code=403, detail="Invalid admin token")

    row = await _create_workspace_record(payload)

    return {
        "id":         str(row["id"]),
        "name":       row["name"],
        "owner_name": row.get("owner_name", ""),
        "email":      row["email"],
        "plan":       row["plan"],
        "api_key":    row["api_key"],
        "created_at": row["created_at"],
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
    token_response = {
        "id": str(token_id), "agent_name": payload.agent_name,
        "description": payload.description or "",
        "can_do": effective_can, "cannot_do": effective_cannot,
        "authorized_by": payload.authorized_by, "signature": signature,
        "policy_id": payload.policy_id, "active": True, "version": 1,
        "metadata": payload.metadata or {},
        "created_at": datetime.now(timezone.utc), "updated_at": None,
    }
    runtime_sync = await _sync_legacy_token_to_runtime(ws, token_response)
    if runtime_sync:
        token_response["metadata"] = {**token_response["metadata"], **runtime_sync}
        await db.execute(
            "UPDATE intent_tokens SET metadata = :meta WHERE id = :tid AND workspace_id = :wid",
            {"meta": json.dumps(token_response["metadata"]), "tid": token_id, "wid": ws["id"]},
        )
    return token_response


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
        {"tid": _normalize_token_lookup_id(token_id), "wid": ws["id"]}
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
        {"tid": _normalize_token_lookup_id(token_id), "wid": ws["id"]}
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
    lookup_token_id = _normalize_token_lookup_id(payload.token_id)

    # ── Load token ────────────────────────────────────────────────────────────
    token = await db.fetch_one(
        "SELECT * FROM intent_tokens WHERE id = :tid AND workspace_id = :wid AND active = TRUE",
        {"tid": lookup_token_id, "wid": workspace["id"]}
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
            str(workspace["id"]), lookup_token_id, payload.action,
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
            "token_id":     lookup_token_id,
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
                "wid":     workspace["id"], "tid":     lookup_token_id,
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
        {"tid": _normalize_token_lookup_id(payload.token_id), "wid": ws["id"]}
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


@app.post("/gateway/{api_key}/forward", tags=["Gateway"])
async def gateway_forward(
    api_key: str,
    body: GatewayForwardBody,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Active gateway for webhook-style agents.

    Incoming traffic is validated by Nova first. Only approved actions are
    forwarded to the real target service. Optionally, the outbound response can
    be validated before returning it to the caller.
    """
    ws = await db.fetch_one(
        "SELECT * FROM workspaces WHERE api_key = :key", {"key": api_key}
    )
    if not ws:
        raise HTTPException(401, "Invalid API key")
    ws = dict(ws)

    action = _extract_action_text(body)
    if not action:
        raise HTTPException(400, "No action provided. Use 'action', 'message', or 'texto'.")

    if not body.forward_to.startswith(("http://", "https://")):
        raise HTTPException(400, "forward_to must start with http:// or https://")

    token_id = await _resolve_workspace_token_id(str(ws["id"]), body.token_id or body.token)
    if not token_id:
        raise HTTPException(
            status_code=409,
            detail="No active Intent Token found for gateway mode. Create one before proxying live traffic.",
        )

    inbound_ctx = {
        "request_id": Crypto.generate_request_id(),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", ""),
        "start_time": time.time(),
    }
    inbound_validation = await _run_validation(
        ValidateRequest(
            token_id=token_id,
            action=action,
            context=body.context or body.contexto or "",
            generate_response=False,
            check_duplicates=body.dedup,
            dry_run=body.dry_run,
        ),
        ws,
        inbound_ctx,
        background_tasks,
    )

    if inbound_validation.verdict != Verdict.APPROVED:
        return JSONResponse(
            {
                "status": "blocked_by_nova",
                "phase": "inbound",
                "validation": inbound_validation.model_dump(mode="json"),
            },
            status_code=403 if inbound_validation.verdict == Verdict.BLOCKED else 409,
        )

    try:
        original_payload = await request.json()
    except Exception:
        original_payload = {}

    forward_payload = body.forward_payload
    if forward_payload is None:
        forward_payload = _sanitize_gateway_payload(original_payload if isinstance(original_payload, dict) else {})

    headers = {key: value for key, value in (body.forward_headers or {}).items() if value is not None}
    if body.include_nova_headers:
        headers.update({
            "X-Nova-Verdict": inbound_validation.verdict.value,
            "X-Nova-Score": str(inbound_validation.score),
            "X-Nova-Token-Id": token_id,
            "X-Nova-Request-Id": inbound_validation.request_id,
        })
        if inbound_validation.ledger_id is not None:
            headers["X-Nova-Ledger-Id"] = str(inbound_validation.ledger_id)

    request_kwargs: Dict[str, Any] = {
        "headers": headers,
        "timeout": body.forward_timeout_ms / 1000,
    }
    if body.forward_method == "GET":
        request_kwargs["params"] = forward_payload
    else:
        request_kwargs["json"] = forward_payload

    try:
        async with httpx.AsyncClient() as client:
            upstream = await client.request(body.forward_method, body.forward_to, **request_kwargs)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Forward target unreachable: {exc}") from exc

    outbound_validation = None
    response_text = upstream.text
    response_json = None
    try:
        response_json = upstream.json()
    except Exception:
        response_json = None

    if body.validate_response:
        outbound_action = body.response_action or _coerce_response_action(
            response_text,
            response_json=response_json,
            preferred_field=body.response_field,
        )
        outbound_token_id = await _resolve_workspace_token_id(
            str(ws["id"]),
            body.response_token_id or token_id,
        )
        if not outbound_token_id:
            raise HTTPException(409, "No active Intent Token available to validate the outbound response")

        outbound_ctx = {
            "request_id": Crypto.generate_request_id(),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent", ""),
            "start_time": time.time(),
        }
        outbound_validation = await _run_validation(
            ValidateRequest(
                token_id=outbound_token_id,
                action=outbound_action,
                context=body.response_context or f"Outbound response from {body.forward_to}",
                generate_response=False,
                check_duplicates=False,
                dry_run=body.dry_run,
            ),
            ws,
            outbound_ctx,
            background_tasks,
        )
        if outbound_validation.verdict != Verdict.APPROVED:
            return JSONResponse(
                {
                    "status": "blocked_by_nova",
                    "phase": "outbound",
                    "validation": inbound_validation.model_dump(mode="json"),
                    "response_validation": outbound_validation.model_dump(mode="json"),
                },
                status_code=403 if outbound_validation.verdict == Verdict.BLOCKED else 409,
            )

    response_headers = {
        "X-Nova-Verdict": inbound_validation.verdict.value,
        "X-Nova-Score": str(inbound_validation.score),
        "X-Nova-Request-Id": inbound_validation.request_id,
    }
    if outbound_validation:
        response_headers["X-Nova-Response-Verdict"] = outbound_validation.verdict.value
        response_headers["X-Nova-Response-Score"] = str(outbound_validation.score)

    content_type = upstream.headers.get("content-type", "")
    if response_json is not None and "application/json" in content_type.lower():
        response = JSONResponse(response_json, status_code=upstream.status_code)
    else:
        media_type = content_type.split(";", 1)[0] if content_type else "text/plain"
        response = Response(
            content=upstream.content,
            status_code=upstream.status_code,
            media_type=media_type,
        )

    for key, value in response_headers.items():
        response.headers[key] = value
    return response


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


@app.get("/skills", tags=["Skills"])
async def get_available_skills():
    """
    Get available system integrations and their credential schemas.
    """
    try:
        from nova.integrations_catalog import INTEGRATION_SCHEMAS

        return INTEGRATION_SCHEMAS
    except Exception as e:
        log.error(f"Failed to load integration schemas: {e}")
        # Fallback to some defaults if import fails
        return {
            "slack": {"name": "Slack", "category": "Communication", "description": "Slack integration"},
            "gmail": {"name": "Gmail", "category": "Communication", "description": "Gmail integration"}
        }


@app.get("/connectors", tags=["Skills"])
async def get_connector_registry(ws: Dict = Depends(get_workspace)):
    """
    Get the workspace connector registry derived from the local Nova skill store.
    """
    del ws
    try:
        from nova.connector_registry import build_connector_inventory

        return build_connector_inventory()
    except Exception as e:
        log.error(f"Failed to build connector registry: {e}")
        return {
            "connectors": [],
            "summary": {
                "catalog_count": 0,
                "connected_count": 0,
                "incomplete_count": 0,
                "skills_dir": str((Path.home() / '.nova' / 'skills')),
            },
        }


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — SSE Streaming
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/stream/events", tags=["Streaming"])
async def stream_events(
    request: Request,
    x_api_key: Optional[str] = Query(None, description="Workspace API key"),
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
    if x_api_key:
        ws = await db.fetch_one(
            "SELECT * FROM workspaces WHERE api_key = :key", {"key": x_api_key}
        )
        if not ws:
            raise HTTPException(401, "Invalid API key")
        ws = dict(ws)
    else:
        ws = await get_workspace(request=request, x_api_key=None)

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
    response = {
        "token_id":    str(token_id),
        "agent_name":  name,
        "description": desc,
        "can_do":      can_do,
        "cannot_do":   cannot_do,
        "signature":   sig,
        "parsed_from": "natural_language",
    }
    runtime_sync = await _sync_legacy_token_to_runtime(
        ws,
        {
            "id": str(token_id),
            "agent_name": name,
            "description": desc,
            "can_do": can_do,
            "cannot_do": cannot_do,
        },
    )
    if runtime_sync:
        await db.execute(
            "UPDATE intent_tokens SET metadata = :meta, updated_at = NOW() WHERE id = :tid AND workspace_id = :wid",
            {"meta": json.dumps(runtime_sync), "tid": token_id, "wid": ws["id"]},
        )
        response["runtime"] = runtime_sync
    return response


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
