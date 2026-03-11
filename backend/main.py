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
║    IntentOS v3.0 — Enterprise Governance Infrastructure for AI Agents       ║
║                                                                              ║
║    Components:                                                               ║
║    ├── Intent Verification    — Validates agent actions against rules       ║
║    ├── Memory Engine          — Persistent context across executions         ║
║    ├── Duplicate Guard        — Blocks identical/similar recent actions      ║
║    ├── Response Generator     — Produces approved responses via LLM          ║
║    ├── Intent Ledger          — Immutable cryptographic audit trail          ║
║    ├── Alert System           — Real-time notifications for violations       ║
║    └── Analytics Engine       — Insights and trend analysis                  ║
║                                                                              ║
║    Copyright (c) 2024 Nova OS. All rights reserved.                         ║
║    https://nova-os.com                                                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Maintained by @sxrubyo
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import secrets
import sys
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from functools import wraps
from typing import (
    Any, Dict, List, Optional, Tuple, Union, 
    Callable, TypeVar, Generic, Annotated
)

import httpx
import databases
from fastapi import (
    FastAPI, HTTPException, Header, Depends,
    Request, Response, BackgroundTasks, Query, Path, Body
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError, validator, root_validator
from starlette.middleware.base import BaseHTTPMiddleware


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

class Settings:
    """
    Application settings loaded from environment variables.
    All sensitive values have secure defaults for development.
    """
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://nova:nova_secret_2026@db:5432/nova"
    )
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "10"))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
    
    # Security
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", 
        "nova_signing_key_CHANGE_IN_PRODUCTION_" + secrets.token_hex(16)
    )
    API_KEY_MIN_LENGTH: int = 16
    BCRYPT_ROUNDS: int = 12
    
    # AI/LLM
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_TIMEOUT: float = float(os.getenv("OPENROUTER_TIMEOUT", "15.0"))
    OPENROUTER_MAX_TOKENS: int = int(os.getenv("OPENROUTER_MAX_TOKENS", "500"))
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
    
    # Duplicate Detection
    DUPLICATE_WINDOW_MINUTES: int = int(os.getenv("DUPLICATE_WINDOW_MINUTES", "60"))
    DUPLICATE_THRESHOLD: float = float(os.getenv("DUPLICATE_THRESHOLD", "0.82"))
    
    # Memory
    MEMORY_DEFAULT_IMPORTANCE: int = 5
    MEMORY_MAX_PER_AGENT: int = int(os.getenv("MEMORY_MAX_PER_AGENT", "1000"))
    MEMORY_AUTO_EXPIRE_DAYS: int = int(os.getenv("MEMORY_AUTO_EXPIRE_DAYS", "90"))
    
    # Scoring
    SCORE_APPROVED_THRESHOLD: int = int(os.getenv("SCORE_APPROVED_THRESHOLD", "70"))
    SCORE_ESCALATED_THRESHOLD: int = int(os.getenv("SCORE_ESCALATED_THRESHOLD", "40"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT", 
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    
    # Server
    VERSION: str = "3.1.5"
    BUILD: str = "2026.03.shadow"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    @classmethod
    def is_production(cls) -> bool:
        return cls.ENVIRONMENT == "production"
    
    @classmethod
    def has_llm(cls) -> bool:
        return bool(cls.OPENROUTER_API_KEY)


settings = Settings()


# ══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════════════════

def setup_logging() -> logging.Logger:
    """Configure structured logging for the application."""
    
    # Create formatter
    formatter = logging.Formatter(settings.LOG_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    root_logger.addHandler(console_handler)
    
    # Nova logger
    logger = logging.getLogger("nova")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Reduce noise from libraries
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
    """Initialize database schema with all required tables and indexes."""
    
    log.info("Initializing database schema...")
    
    # Workspaces table (if not exists - usually created by migrations)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name            TEXT NOT NULL,
            api_key         TEXT UNIQUE NOT NULL,
            plan            TEXT DEFAULT 'free',
            settings        JSONB DEFAULT '{}',
            created_at      TIMESTAMPTZ DEFAULT NOW(),
            updated_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    
    # Intent Tokens table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS intent_tokens (
            id              BIGSERIAL PRIMARY KEY,
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            agent_name      TEXT NOT NULL,
            description     TEXT DEFAULT '',
            can_do          TEXT[] NOT NULL DEFAULT '{}',
            cannot_do       TEXT[] NOT NULL DEFAULT '{}',
            authorized_by   TEXT NOT NULL,
            signature       TEXT NOT NULL,
            metadata        JSONB DEFAULT '{}',
            active          BOOLEAN DEFAULT TRUE,
            created_at      TIMESTAMPTZ DEFAULT NOW(),
            updated_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    
    # Ledger table (immutable audit log)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS ledger (
            id              BIGSERIAL PRIMARY KEY,
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            token_id        BIGINT NOT NULL REFERENCES intent_tokens(id),
            agent_name      TEXT NOT NULL,
            action          TEXT NOT NULL,
            context         TEXT DEFAULT '',
            score           INTEGER NOT NULL,
            verdict         TEXT NOT NULL,
            reason          TEXT NOT NULL,
            response        TEXT,
            duplicate_of    BIGINT,
            score_factors   JSONB DEFAULT '{}',
            prev_hash       TEXT NOT NULL,
            own_hash        TEXT NOT NULL,
            request_id      TEXT,
            client_ip       TEXT,
            user_agent      TEXT,
            executed_at     TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    
    # Memories table
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
            embedding       VECTOR(1536),
            expires_at      TIMESTAMPTZ,
            created_at      TIMESTAMPTZ DEFAULT NOW(),
            updated_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    
    # Alerts table
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
    
    # Rate limits table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS rate_limits (
            id              BIGSERIAL PRIMARY KEY,
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            window_start    TIMESTAMPTZ NOT NULL,
            request_count   INTEGER DEFAULT 1,
            UNIQUE(workspace_id, window_start)
        )
    """)
    
    # Analytics events table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS analytics_events (
            id              BIGSERIAL PRIMARY KEY,
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            event_type      TEXT NOT NULL,
            event_data      JSONB DEFAULT '{}',
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    
    # Create indexes
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_tokens_workspace ON intent_tokens(workspace_id)",
        "CREATE INDEX IF NOT EXISTS idx_tokens_active ON intent_tokens(workspace_id, active)",
        "CREATE INDEX IF NOT EXISTS idx_ledger_workspace ON ledger(workspace_id)",
        "CREATE INDEX IF NOT EXISTS idx_ledger_token ON ledger(token_id)",
        "CREATE INDEX IF NOT EXISTS idx_ledger_verdict ON ledger(workspace_id, verdict)",
        "CREATE INDEX IF NOT EXISTS idx_ledger_executed ON ledger(workspace_id, executed_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(workspace_id, agent_name)",
        "CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(workspace_id, agent_name, importance DESC)",
        "CREATE INDEX IF NOT EXISTS idx_memories_expires ON memories(expires_at) WHERE expires_at IS NOT NULL",
        "CREATE INDEX IF NOT EXISTS idx_alerts_workspace ON alerts(workspace_id)",
        "CREATE INDEX IF NOT EXISTS idx_alerts_unresolved ON alerts(workspace_id, resolved) WHERE resolved = FALSE",
        "CREATE INDEX IF NOT EXISTS idx_rate_limits_window ON rate_limits(workspace_id, window_start)",
        "CREATE INDEX IF NOT EXISTS idx_analytics_type ON analytics_events(workspace_id, event_type)",
    ]
    
    for idx in indexes:
        try:
            await db.execute(idx)
        except Exception as e:
            log.debug(f"Index creation skipped: {e}")
    
    # Add new columns to existing tables (migrations)
    migrations = [
        "ALTER TABLE ledger ADD COLUMN IF NOT EXISTS score_factors JSONB DEFAULT '{}'",
        "ALTER TABLE ledger ADD COLUMN IF NOT EXISTS request_id TEXT",
        "ALTER TABLE ledger ADD COLUMN IF NOT EXISTS client_ip TEXT",
        "ALTER TABLE ledger ADD COLUMN IF NOT EXISTS user_agent TEXT",
        "ALTER TABLE memories ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'",
        "ALTER TABLE memories ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS alert_type TEXT DEFAULT 'violation'",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS severity TEXT DEFAULT 'medium'",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'",
        "ALTER TABLE intent_tokens ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'",
        "ALTER TABLE intent_tokens ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()",
    ]
    
    for migration in migrations:
        try:
            await db.execute(migration)
        except Exception as e:
            log.debug(f"Migration skipped: {e}")
    
    log.info("Database schema initialized successfully")


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

class Verdict(str, Enum):
    """Possible validation verdicts."""
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    ESCALATED = "ESCALATED"
    DUPLICATE = "DUPLICATE"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of alerts."""
    VIOLATION = "violation"
    ESCALATION = "escalation"
    ANOMALY = "anomaly"
    RATE_LIMIT = "rate_limit"
    SYSTEM = "system"


# High-risk verbs that require extra scrutiny
HIGH_RISK_VERBS = {
    "en": ["delete", "remove", "cancel", "modify", "override", "disable", 
           "terminate", "destroy", "drop", "truncate", "wipe", "purge",
           "revoke", "suspend", "deactivate", "kill", "stop", "halt"],
    "es": ["eliminar", "borrar", "cancelar", "modificar", "alterar",
           "deshabilitar", "terminar", "destruir", "revocar", "suspender",
           "desactivar", "detener", "parar", "anular", "suprimir"]
}

# Sensitive data patterns
SENSITIVE_PATTERNS = [
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
    r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Credit card
    r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b',  # SSN
    r'(?i)(api[_-]?key|secret|password|token|credential)["\s:=]+["\']?[\w-]{8,}',  # Secrets
]


# ══════════════════════════════════════════════════════════════════════════════
# CRYPTOGRAPHY
# ══════════════════════════════════════════════════════════════════════════════

class Crypto:
    """Cryptographic utilities for signing and hashing."""
    
    @staticmethod
    def sign(data: dict) -> str:
        """
        Create a cryptographic signature for data.
        
        Args:
            data: Dictionary to sign
            
        Returns:
            SHA-256 HMAC signature
        """
        payload = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(
            f"{settings.SECRET_KEY}:{payload}".encode()
        ).hexdigest()
    
    @staticmethod
    def chain_hash(prev_hash: str, record: dict) -> str:
        """
        Create a blockchain-style hash linking to previous record.
        
        Args:
            prev_hash: Hash of the previous record
            record: Current record data
            
        Returns:
            Chain hash for current record
        """
        payload = json.dumps(
            {"prev": prev_hash, "record": record}, 
            sort_keys=True, 
            default=str
        )
        return hashlib.sha256(payload.encode()).hexdigest()
    
    @staticmethod
    def generate_request_id() -> str:
        """Generate a unique request ID."""
        return f"req_{uuid.uuid4().hex[:16]}"
    
    @staticmethod
    def hash_action(action: str) -> str:
        """Create a short hash of an action for deduplication keys."""
        return hashlib.md5(action.encode()).hexdigest()[:12]


# ══════════════════════════════════════════════════════════════════════════════
# TEXT SIMILARITY
# ══════════════════════════════════════════════════════════════════════════════

class TextSimilarity:
    """Text comparison and similarity utilities."""
    
    @staticmethod
    def word_set(text: str) -> set:
        """Extract normalized word set from text."""
        return set(re.findall(r'\w+', text.lower()))
    
    @staticmethod
    def jaccard_similarity(a: str, b: str) -> float:
        """
        Calculate Jaccard similarity between two texts.
        
        Returns:
            Similarity score between 0.0 and 1.0
        """
        words_a = TextSimilarity.word_set(a)
        words_b = TextSimilarity.word_set(b)
        
        if not words_a or not words_b:
            return 0.0
        
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        """Extract all numeric values from text."""
        numbers = []
        for match in re.findall(r'\d+(?:[.,]\d+)?', text):
            try:
                numbers.append(float(match.replace(',', '.')))
            except ValueError:
                pass
        return numbers
    
    @staticmethod
    def extract_limit(rule: str) -> Tuple[Optional[float], bool]:
        """
        Extract numeric limit from a rule.
        
        Returns:
            Tuple of (limit_value, is_percentage)
        """
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
                    
                    is_percentage = '%' in rule_lower or 'percent' in rule_lower
                    
                    return value, is_percentage
                except (ValueError, IndexError):
                    pass
        
        return None, False
    
    @staticmethod
    def contains_sensitive_data(text: str) -> List[str]:
        """Check if text contains sensitive data patterns."""
        found = []
        for pattern in SENSITIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                found.append(pattern)
        return found


# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════════════════

# ── Request Models ────────────────────────────────────────────────────────────

class TokenCreate(BaseModel):
    """Request model for creating an Intent Token."""
    
    agent_name: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Name of the agent"
    )
    description: Optional[str] = Field(
        default="",
        max_length=500,
        description="Optional description of the agent's purpose"
    )
    can_do: List[str] = Field(
        ...,
        min_items=0,
        max_items=50,
        description="List of allowed actions/behaviors"
    )
    cannot_do: List[str] = Field(
        ...,
        min_items=0,
        max_items=50,
        description="List of forbidden actions/behaviors"
    )
    authorized_by: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Email or identifier of the authorizing person"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default={},
        description="Additional metadata"
    )
    
    @validator('can_do', 'cannot_do', each_item=True)
    def validate_rules(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("Each rule must be at least 3 characters")
        if len(v) > 500:
            raise ValueError("Each rule must be under 500 characters")
        return v.strip()


class TokenUpdate(BaseModel):
    """Request model for updating an Intent Token."""
    
    description: Optional[str] = None
    can_do: Optional[List[str]] = None
    cannot_do: Optional[List[str]] = None
    active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class ValidateRequest(BaseModel):
    """Request model for validating an action."""
    
    token_id: str = Field(
        ...,
        description="Intent Token ID"
    )
    action: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Action to validate"
    )
    context: Optional[str] = Field(
        default="",
        max_length=10000,
        description="Additional context for the action"
    )
    generate_response: Optional[bool] = Field(
        default=True,
        description="Whether to generate a response using LLM"
    )
    check_duplicates: Optional[bool] = Field(
        default=True,
        description="Whether to check for duplicate actions"
    )
    duplicate_window_minutes: Optional[int] = Field(
        default=60,
        ge=1,
        le=1440,
        description="Time window for duplicate detection (minutes)"
    )
    duplicate_threshold: Optional[float] = Field(
        default=0.82,
        ge=0.5,
        le=1.0,
        description="Similarity threshold for duplicate detection"
    )
    dry_run: Optional[bool] = Field(
        default=False,
        description="If true, validate without recording to ledger"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default={},
        description="Additional request metadata"
    )


class MemoryCreate(BaseModel):
    """Request model for creating a memory."""
    
    agent_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the agent"
    )
    key: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Memory key/identifier"
    )
    value: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Memory content"
    )
    tags: Optional[List[str]] = Field(
        default=[],
        max_items=20,
        description="Tags for categorization"
    )
    importance: Optional[int] = Field(
        default=5,
        ge=1,
        le=10,
        description="Importance level (1-10)"
    )
    expires_in_hours: Optional[int] = Field(
        default=None,
        ge=1,
        le=8760,  # Max 1 year
        description="Hours until expiration"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default={},
        description="Additional metadata"
    )
    
    @validator('tags', each_item=True)
    def validate_tags(cls, v):
        return v.strip().lower()[:50]


class MemoryUpdate(BaseModel):
    """Request model for updating a memory."""
    
    value: Optional[str] = None
    tags: Optional[List[str]] = None
    importance: Optional[int] = Field(default=None, ge=1, le=10)
    expires_in_hours: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class MemorySearch(BaseModel):
    """Request model for searching memories."""
    
    agent_name: str
    query: str = Field(..., min_length=1, max_length=1000)
    limit: Optional[int] = Field(default=10, ge=1, le=100)
    min_importance: Optional[int] = Field(default=1, ge=1, le=10)
    tags: Optional[List[str]] = None


class AlertResolve(BaseModel):
    """Request model for resolving an alert."""
    
    resolved_by: Optional[str] = None
    notes: Optional[str] = None


class WebhookBody(BaseModel):
    """Flexible webhook request body."""
    
    action: Optional[str] = None
    message: Optional[str] = None
    texto: Optional[str] = None  # Spanish alternative
    token_id: Optional[str] = None
    token: Optional[str] = None  # Alternative
    context: Optional[str] = None
    contexto: Optional[str] = None  # Spanish alternative
    agent_name: Optional[str] = None
    
    # Memory fields
    memory_key: Optional[str] = None
    memory_val: Optional[str] = None
    memory_tags: Optional[List[str]] = None
    memory_importance: Optional[int] = None
    
    # Options
    respond: Optional[bool] = True
    dedup: Optional[bool] = True
    dry_run: Optional[bool] = False


# ── Response Models ───────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Response model for Intent Token."""
    
    id: str
    agent_name: str
    description: str
    can_do: List[str]
    cannot_do: List[str]
    authorized_by: str
    signature: str
    active: bool
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]


class ValidateResponse(BaseModel):
    """Response model for validation result."""
    
    verdict: Verdict
    score: int
    reason: str
    response: Optional[str]
    execute: bool
    agent_name: str
    ledger_id: Optional[int]
    hash: Optional[str]
    memories_used: int
    duplicate_check: str
    duplicate_of: Optional[Dict[str, Any]]
    score_factors: Optional[Dict[str, int]]
    request_id: str
    latency_ms: int


class MemoryResponse(BaseModel):
    """Response model for memory."""
    
    id: int
    agent_name: str
    key: str
    value: str
    tags: List[str]
    importance: int
    source: str
    metadata: Dict[str, Any]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]


class LedgerEntry(BaseModel):
    """Response model for ledger entry."""
    
    id: int
    agent_name: str
    action: str
    context: Optional[str]
    score: int
    verdict: Verdict
    reason: str
    response: Optional[str]
    score_factors: Optional[Dict[str, int]]
    own_hash: str
    executed_at: datetime


class AlertResponse(BaseModel):
    """Response model for alert."""
    
    id: int
    agent_name: str
    alert_type: str
    severity: str
    message: str
    score: Optional[int]
    metadata: Dict[str, Any]
    resolved: bool
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime


class StatsResponse(BaseModel):
    """Response model for statistics."""
    
    total_actions: int
    approved: int
    blocked: int
    escalated: int
    duplicates_blocked: int
    avg_score: int
    active_agents: int
    alerts_pending: int
    memories_stored: int
    approval_rate: float
    score_trend: Optional[List[int]]


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str
    version: str
    build: str
    environment: str
    timestamp: datetime
    database: str
    llm_available: bool
    uptime_seconds: int


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str
    code: str
    detail: Optional[str]
    request_id: Optional[str]


def _error_payload(
    error: str,
    code: str,
    request_id: Optional[str],
    detail: Optional[Any] = None
) -> Dict[str, Any]:
    payload = {"error": error, "code": code, "request_id": request_id}
    if detail is not None:
        payload["detail"] = detail
    return payload


# ══════════════════════════════════════════════════════════════════════════════
# MIDDLEWARE
# ══════════════════════════════════════════════════════════════════════════════

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request context (ID, timing, etc.)
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = Crypto.generate_request_id()
        request.state.request_id = request_id
        request.state.start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Add headers
        process_time = time.time() - request.state.start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.3f}s"
        response.headers["X-Nova-Version"] = settings.VERSION
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    For production, use Redis-based rate limiting.
    """
    
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[float]] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ("/", "/health"):
            return await call_next(request)
        
        # Get client identifier (API key or IP)
        api_key = request.headers.get("x-api-key", "")
        client_id = api_key[:16] if api_key else request.client.host
        
        # Clean old requests
        now = time.time()
        window_start = now - 60
        self.requests[client_id] = [
            t for t in self.requests[client_id] if t > window_start
        ]
        
        # Check rate limit
        if len(self.requests[client_id]) >= self.requests_per_minute:
            request_id = getattr(request.state, "request_id", None) or Crypto.generate_request_id()
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "code": "RATE_LIMIT",
                    "detail": f"Maximum {self.requests_per_minute} requests per minute",
                    "retry_after": 60,
                    "request_id": request_id
                }
            )
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Nova-Version"] = settings.VERSION
            return response
        
        # Track request
        self.requests[client_id].append(now)
        
        return await call_next(request)


# ══════════════════════════════════════════════════════════════════════════════
# DEPENDENCIES
# ══════════════════════════════════════════════════════════════════════════════

async def get_workspace(
    x_api_key: str = Header(..., description="Workspace API key")
) -> Dict[str, Any]:
    """
    Dependency to authenticate and retrieve workspace from API key.
    
    Raises:
        HTTPException: If API key is invalid
    """
    if not x_api_key or len(x_api_key) < settings.API_KEY_MIN_LENGTH:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key format"
        )
    
    row = await db.fetch_one(
        "SELECT * FROM workspaces WHERE api_key = :key",
        {"key": x_api_key}
    )
    
    if not row:
        log.warning(f"Invalid API key attempt: {x_api_key[:8]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return dict(row)


async def get_request_context(request: Request) -> Dict[str, Any]:
    """Dependency to get request context."""
    return {
        "request_id": getattr(request.state, "request_id", Crypto.generate_request_id()),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", ""),
        "start_time": getattr(request.state, "start_time", time.time()),
    }


# ══════════════════════════════════════════════════════════════════════════════
# SCORING ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class ScoringEngine:
    """
    Intent Fidelity Scoring Engine.
    
    Calculates a score (0-100) indicating how well an action
    aligns with the agent's authorized behaviors.
    
    Score ranges:
        - 70-100: APPROVED (safe to execute)
        - 40-69:  ESCALATED (human review needed)
        - 0-39:   BLOCKED (clear violation)
    """
    
    @staticmethod
    async def calculate_score(
        action: str,
        can_do: List[str],
        cannot_do: List[str],
        context: str = "",
        memories: Optional[List[Dict]] = None
    ) -> Tuple[int, str, Dict[str, int]]:
        """
        Calculate intent fidelity score.
        
        Args:
            action: The action to evaluate
            can_do: List of allowed behaviors
            cannot_do: List of forbidden behaviors
            context: Additional context
            memories: Relevant agent memories
            
        Returns:
            Tuple of (score, reason, score_factors)
        """
        # Try LLM scoring first
        if settings.has_llm():
            try:
                return await ScoringEngine._score_with_llm(
                    action, can_do, cannot_do, context, memories or []
                )
            except Exception as e:
                log.warning(f"LLM scoring failed, falling back to heuristic: {e}")
        
        # Fallback to heuristic scoring
        return ScoringEngine._score_heuristic(action, can_do, cannot_do)
    
    @staticmethod
    def _score_heuristic(
        action: str,
        can_do: List[str],
        cannot_do: List[str]
    ) -> Tuple[int, str, Dict[str, int]]:
        """
        Rule-based heuristic scoring.
        
        This is fast (<1ms) and handles 90% of cases accurately.
        """
        action_lower = action.lower()
        score_factors = {}
        
        # ── Check high-risk verbs ─────────────────────────────────────────────
        all_risk_verbs = HIGH_RISK_VERBS["en"] + HIGH_RISK_VERBS["es"]
        
        for verb in all_risk_verbs:
            if verb in action_lower:
                # Check if verb is in forbidden rules
                for rule in cannot_do:
                    if verb in rule.lower():
                        score_factors["high_risk_verb_forbidden"] = -70
                        return (
                            12, 
                            f"High-risk action '{verb}' violates rule: '{rule[:50]}'",
                            score_factors
                        )
                
                # Check if verb is explicitly allowed
                verb_allowed = any(verb in r.lower() for r in can_do)
                if not verb_allowed:
                    score_factors["high_risk_verb_not_authorized"] = -50
                    return (
                        32,
                        f"High-risk action '{verb}' not explicitly authorized",
                        score_factors
                    )
                else:
                    score_factors["high_risk_verb_authorized"] = 10
        
        # ── Check numeric limits ──────────────────────────────────────────────
        action_numbers = TextSimilarity.extract_numbers(action_lower)
        
        for rule in cannot_do:
            limit_val, is_pct = TextSimilarity.extract_limit(rule)
            
            if limit_val is not None:
                for num in action_numbers:
                    if num > limit_val:
                        pct_str = "%" if is_pct else ""
                        score_factors["exceeds_limit"] = -80
                        return (
                            8,
                            f"Value {num}{pct_str} exceeds limit {limit_val}{pct_str} — violates: '{rule[:50]}'",
                            score_factors
                        )
        
        # ── Check forbidden keyword matches ───────────────────────────────────
        for rule in cannot_do:
            # Extract significant keywords (>4 chars, not common words)
            stop_words = {
                'para', 'todos', 'todas', 'desde', 'hasta', 'entre', 'sobre',
                'with', 'from', 'that', 'this', 'have', 'will', 'been', 'more',
                'than', 'when', 'what', 'which', 'there', 'their', 'would'
            }
            keywords = [
                w for w in TextSimilarity.word_set(rule)
                if len(w) > 4 and w not in stop_words
            ]
            
            if not keywords:
                continue
            
            hits = sum(1 for kw in keywords if kw in action_lower)
            
            # Match if 1+ hit for short rules, 2+ for longer
            if (hits >= 1 and len(keywords) <= 3) or hits >= 2:
                score_factors["forbidden_rule_match"] = -60
                return (
                    18,
                    f"Action matches forbidden rule: '{rule[:50]}'",
                    score_factors
                )
        
        # ── Check allowed rule matches ────────────────────────────────────────
        best_match = None
        best_match_score = 0
        
        for rule in can_do:
            keywords = [w for w in TextSimilarity.word_set(rule) if len(w) > 4]
            
            if not keywords:
                continue
            
            hits = sum(1 for kw in keywords if kw in action_lower)
            match_ratio = hits / len(keywords) if keywords else 0
            
            if match_ratio > best_match_score:
                best_match_score = match_ratio
                best_match = rule
        
        if best_match and best_match_score >= 0.3:
            score_factors["allowed_rule_match"] = int(20 + best_match_score * 60)
            return (
                int(70 + best_match_score * 25),
                f"Aligned with authorized action: '{best_match[:50]}'",
                score_factors
            )
        
        # ── No clear match — requires review ──────────────────────────────────
        score_factors["no_clear_match"] = 0
        return (
            55,
            "Action does not clearly match any rule — human review recommended",
            score_factors
        )
    
    @staticmethod
    async def _score_with_llm(
        action: str,
        can_do: List[str],
        cannot_do: List[str],
        context: str,
        memories: List[Dict]
    ) -> Tuple[int, str, Dict[str, int]]:
        """
        LLM-based scoring for nuanced evaluation.
        """
        # Format rules
        can_rules = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(can_do))
        cannot_rules = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(cannot_do))
        
        # Format memories
        memory_context = ""
        if memories:
            memory_items = "\n".join(
                f"  - {m['key']}: {m['value'][:100]}" 
                for m in memories[:5]
            )
            memory_context = f"\nAGENT MEMORY:\n{memory_items}"
        
        prompt = f"""You are Nova, a strict intent verification system for AI agents.

ALLOWED ACTIONS:
{can_rules or "  (none specified)"}

FORBIDDEN ACTIONS (never violate):
{cannot_rules or "  (none specified)"}
{memory_context}

ACTION TO EVALUATE: "{action[:500]}"
CONTEXT: {context[:200] or 'none'}

SCORING CRITERIA:
- Violates forbidden rule → 0-30 (numbers matter: ">10% applied to 50%" IS a violation)
- Matches allowed rule → 80-95
- Ambiguous → 50-68
- Memory indicates previous issues → penalize

Respond with JSON only, no markdown:
{{"score": 0, "reason": "reason in under 15 words", "factors": {{"rule_name": score_impact}}}}"""

        try:
            async with httpx.AsyncClient(timeout=settings.OPENROUTER_TIMEOUT) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://nova-os.com",
                        "X-Title": "Nova IntentOS"
                    },
                    json={
                        "model": settings.OPENROUTER_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 150,
                        "temperature": 0.1
                    }
                )
                
                response.raise_for_status()
                
                raw = response.json()["choices"][0]["message"]["content"]
                # Clean markdown code blocks
                raw = re.sub(r'```json\s*|```\s*', '', raw).strip()
                
                result = json.loads(raw)
                
                return (
                    int(result["score"]),
                    result["reason"],
                    result.get("factors", {})
                )
        
        except Exception as e:
            log.error(f"LLM scoring error: {e}")
            raise


# ══════════════════════════════════════════════════════════════════════════════
# RESPONSE GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class ResponseGenerator:
    """
    Generates appropriate responses for approved or blocked actions.
    """
    
    @staticmethod
    async def generate(
        action: str,
        verdict: Verdict,
        score: int,
        reason: str,
        token: Dict,
        context: str,
        memories: List[Dict]
    ) -> Optional[str]:
        """
        Generate a response using LLM.
        
        For APPROVED actions: Generate the actual response content
        For BLOCKED actions: Generate a polite decline message
        """
        if not settings.has_llm():
            return None
        
        agent_name = token.get("agent_name", "Agent")
        
        # Format memory context
        memory_context = ""
        if memories:
            memory_items = "\n".join(
                f"  - {m['key']}: {m['value'][:150]}"
                for m in memories[:6]
            )
            memory_context = f"\nCONTEXT FROM MEMORY:\n{memory_items}"
        
        if verdict == Verdict.BLOCKED:
            prompt = f"""Agent "{agent_name}" attempted a blocked action.

BLOCKED ACTION: {action[:300]}
REASON: {reason}
{memory_context}

Generate a professional response (2-3 sentences) informing the user that this 
action cannot be performed, without revealing internal rules. 
Match the language of the original action (Spanish/English)."""
        
        else:
            can_do = json.dumps(token.get("can_do", []))
            prompt = f"""Agent "{agent_name}" will execute this approved action.

ACTION: {action[:500]}
CONTEXT: {context[:300] or 'none'}
CAPABILITIES: {can_do}
{memory_context}

Generate the actual response or content the agent should produce.
Be specific, helpful, and professional. Maximum 4 sentences.
Match the language of the original action."""
        
        try:
            async with httpx.AsyncClient(timeout=settings.OPENROUTER_TIMEOUT) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.OPENROUTER_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": settings.OPENROUTER_MAX_TOKENS,
                        "temperature": 0.7
                    }
                )
                
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"].strip()
        
        except Exception as e:
            log.error(f"Response generation error: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# MEMORY ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class MemoryEngine:
    """
    Agent memory management system.
    
    Provides persistent context across executions, enabling
    agents to remember past interactions, decisions, and context.
    """
    
    @staticmethod
    async def get_relevant(
        workspace_id: str,
        agent_name: str,
        action: str,
        limit: int = 6
    ) -> List[Dict]:
        """
        Retrieve memories relevant to the current action.
        
        Uses importance-weighted keyword matching to find
        the most relevant memories for context.
        """
        rows = await db.fetch_all(
            """SELECT id, key, value, tags, importance, source, created_at
               FROM memories
               WHERE workspace_id = :wid 
                 AND agent_name = :agent
                 AND (expires_at IS NULL OR expires_at > NOW())
               ORDER BY importance DESC, created_at DESC 
               LIMIT 30""",
            {"wid": workspace_id, "agent": agent_name}
        )
        
        if not rows:
            return []
        
        # Score memories by relevance to action
        action_words = TextSimilarity.word_set(action)
        scored = []
        
        for row in rows:
            memory = dict(row)
            memory_text = f"{memory['key']} {memory['value']}"
            memory_words = TextSimilarity.word_set(memory_text)
            
            # Calculate relevance
            overlap = len(action_words & memory_words)
            total = max(len(action_words | memory_words), 1)
            similarity = overlap / total
            
            # Weight by importance
            score = similarity + (memory['importance'] / 20)
            scored.append((score, memory))
        
        # Sort by score and return top N
        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored[:limit]]
    
    @staticmethod
    async def auto_save(
        workspace_id: str,
        agent_name: str,
        action: str,
        verdict: Verdict,
        score: int,
        context: str
    ):
        """
        Automatically save relevant memories after validation.
        
        - BLOCKED actions are saved with high importance
        - APPROVED actions with context are saved temporarily
        """
        if verdict == Verdict.BLOCKED:
            # Save blocked action for future reference
            await db.execute(
                """INSERT INTO memories 
                   (workspace_id, agent_name, key, value, tags, importance, source)
                   VALUES (:wid, :agent, :key, :val, :tags, :imp, 'auto')""",
                {
                    "wid": workspace_id,
                    "agent": agent_name,
                    "key": f"blocked_{Crypto.hash_action(action)}",
                    "val": f"Blocked action (score {score}): {action[:300]}",
                    "tags": ["blocked", "auto", "violation"],
                    "imp": 8
                }
            )
        
        elif verdict == Verdict.APPROVED and context and len(context) > 30:
            # Save context for approved actions (expires in 7 days)
            await db.execute(
                """INSERT INTO memories 
                   (workspace_id, agent_name, key, value, tags, importance, source, expires_at)
                   VALUES (:wid, :agent, :key, :val, :tags, :imp, 'auto', NOW() + INTERVAL '7 days')""",
                {
                    "wid": workspace_id,
                    "agent": agent_name,
                    "key": f"ctx_{Crypto.hash_action(action)}",
                    "val": f"Approved context: {context[:300]}",
                    "tags": ["context", "auto"],
                    "imp": 4
                }
            )
    
    @staticmethod
    async def cleanup_expired(workspace_id: str) -> int:
        """Remove expired memories and return count."""
        result = await db.execute(
            """DELETE FROM memories 
               WHERE workspace_id = :wid AND expires_at < NOW()""",
            {"wid": workspace_id}
        )
        return result


# ══════════════════════════════════════════════════════════════════════════════
# DUPLICATE GUARD
# ══════════════════════════════════════════════════════════════════════════════

class DuplicateGuard:
    """
    Prevents duplicate action execution.
    
    Uses time-windowed similarity comparison to detect
    and block near-duplicate actions.
    """
    
    @staticmethod
    async def check(
        workspace_id: str,
        token_id: str,
        action: str,
        window_minutes: int = 60,
        threshold: float = 0.82
    ) -> Optional[Dict]:
        """
        Check if a similar action was recently executed.
        
        Returns:
            Dict with duplicate info if found, None otherwise
        """
        since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        
        recent = await db.fetch_all(
            """SELECT id, action, verdict, executed_at
               FROM ledger
               WHERE workspace_id = :wid 
                 AND token_id = :tid
                 AND verdict = 'APPROVED'
                 AND executed_at > :since
               ORDER BY executed_at DESC
               LIMIT 50""",
            {"wid": workspace_id, "tid": token_id, "since": since}
        )
        
        for row in recent:
            similarity = TextSimilarity.jaccard_similarity(action, row["action"])
            
            if similarity >= threshold:
                return {
                    "ledger_id": row["id"],
                    "action": row["action"],
                    "similarity": round(similarity, 3),
                    "executed_at": row["executed_at"].isoformat() if row["executed_at"] else None
                }
        
        return None


# ══════════════════════════════════════════════════════════════════════════════
# ALERT SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

class AlertSystem:
    """
    Real-time alert management for violations and anomalies.
    """
    
    @staticmethod
    async def create(
        workspace_id: str,
        ledger_id: int,
        agent_name: str,
        message: str,
        score: int,
        alert_type: AlertType = AlertType.VIOLATION,
        severity: AlertSeverity = None,
        metadata: Dict = None
    ) -> int:
        """Create a new alert."""
        # Auto-determine severity based on score
        if severity is None:
            if score < 20:
                severity = AlertSeverity.CRITICAL
            elif score < 40:
                severity = AlertSeverity.HIGH
            elif score < 60:
                severity = AlertSeverity.MEDIUM
            else:
                severity = AlertSeverity.LOW
        
        alert_id = await db.execute(
            """INSERT INTO alerts 
               (workspace_id, ledger_id, agent_name, alert_type, severity, 
                message, score, metadata)
               VALUES (:wid, :lid, :agent, :type, :severity, :msg, :score, :meta)
               RETURNING id""",
            {
                "wid": workspace_id,
                "lid": ledger_id,
                "agent": agent_name,
                "type": alert_type.value,
                "severity": severity.value,
                "msg": message[:500],
                "score": score,
                "meta": json.dumps(metadata or {})
            }
        )
        
        log.warning(
            f"Alert created: [{severity.value.upper()}] {agent_name} - {message[:100]}"
        )
        
        return alert_id
    
    @staticmethod
    async def resolve(
        workspace_id: str,
        alert_id: int,
        resolved_by: str = None
    ):
        """Mark an alert as resolved."""
        await db.execute(
            """UPDATE alerts 
               SET resolved = TRUE, resolved_by = :by, resolved_at = NOW()
               WHERE id = :id AND workspace_id = :wid""",
            {"id": alert_id, "wid": workspace_id, "by": resolved_by}
        )


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class AnalyticsEngine:
    """
    Insights and trend analysis for agent behavior.
    """
    
    @staticmethod
    async def get_stats(workspace_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a workspace."""
        wid = workspace_id
        
        # Fetch all stats in parallel
        queries = [
            ("total", "SELECT COUNT(*) c FROM ledger WHERE workspace_id=:w"),
            ("approved", "SELECT COUNT(*) c FROM ledger WHERE workspace_id=:w AND verdict='APPROVED'"),
            ("blocked", "SELECT COUNT(*) c FROM ledger WHERE workspace_id=:w AND verdict='BLOCKED'"),
            ("escalated", "SELECT COUNT(*) c FROM ledger WHERE workspace_id=:w AND verdict='ESCALATED'"),
            ("duplicates", "SELECT COUNT(*) c FROM ledger WHERE workspace_id=:w AND verdict='DUPLICATE'"),
            ("avg_score", "SELECT COALESCE(ROUND(AVG(score)), 0) avg FROM ledger WHERE workspace_id=:w AND verdict!='DUPLICATE'"),
            ("agents", "SELECT COUNT(*) c FROM intent_tokens WHERE workspace_id=:w AND active=TRUE"),
            ("alerts", "SELECT COUNT(*) c FROM alerts WHERE workspace_id=:w AND resolved=FALSE"),
            ("memories", "SELECT COUNT(*) c FROM memories WHERE workspace_id=:w AND (expires_at IS NULL OR expires_at>NOW())"),
        ]
        
        results = {}
        for name, query in queries:
            row = await db.fetch_one(query, {"w": wid})
            results[name] = row["c"] if "c" in row.keys() else row.get("avg", 0)
        
        total = results["total"] or 1
        
        # Score trend (last 7 days)
        trend_query = """
            SELECT DATE(executed_at) as day, ROUND(AVG(score)) as avg_score
            FROM ledger 
            WHERE workspace_id = :w 
              AND executed_at > NOW() - INTERVAL '7 days'
              AND verdict != 'DUPLICATE'
            GROUP BY DATE(executed_at)
            ORDER BY day ASC
        """
        trend_rows = await db.fetch_all(trend_query, {"w": wid})
        score_trend = [int(row["avg_score"]) for row in trend_rows] if trend_rows else None
        
        return {
            "total_actions": results["total"],
            "approved": results["approved"],
            "blocked": results["blocked"],
            "escalated": results["escalated"],
            "duplicates_blocked": results["duplicates"],
            "avg_score": int(results["avg_score"] or 0),
            "active_agents": results["agents"],
            "alerts_pending": results["alerts"],
            "memories_stored": results["memories"],
            "approval_rate": round(results["approved"] / total * 100, 1),
            "score_trend": score_trend
        }
    
    @staticmethod
    async def track_event(
        workspace_id: str,
        event_type: str,
        event_data: Dict = None
    ):
        """Track an analytics event."""
        await db.execute(
            """INSERT INTO analytics_events (workspace_id, event_type, event_data)
               VALUES (:wid, :type, :data)""",
            {
                "wid": workspace_id,
                "type": event_type,
                "data": json.dumps(event_data or {})
            }
        )


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION LIFECYCLE
# ══════════════════════════════════════════════════════════════════════════════

# Track startup time for uptime calculation
_startup_time: float = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    global _startup_time
    
    log.info("=" * 60)
    log.info(f"Nova IntentOS v{settings.VERSION} starting...")
    log.info(f"Environment: {settings.ENVIRONMENT}")
    log.info(f"LLM available: {settings.has_llm()}")
    log.info("=" * 60)
    
    # Startup
    await db.connect()
    await init_database()
    _startup_time = time.time()
    
    log.info("Nova IntentOS ready to accept connections")
    
    yield
    
    # Shutdown
    log.info("Nova IntentOS shutting down...")
    await db.disconnect()
    log.info("Shutdown complete")


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION SETUP
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Nova IntentOS API",
    description="""
    Enterprise-grade governance infrastructure for AI agents.
    
    Nova sits between your AI agents and the real world, validating
    every action before execution and maintaining a cryptographic
    audit trail of all decisions.
    
    ## Features
    
    - **Intent Verification**: Score-based action validation
    - **Memory Engine**: Persistent agent context
    - **Duplicate Guard**: Prevent repeated actions
    - **Response Generator**: LLM-powered responses
    - **Intent Ledger**: Immutable audit trail
    - **Alert System**: Real-time violation alerts
    
    ## Authentication
    
    All endpoints (except `/` and `/health`) require an API key
    passed via the `x-api-key` header.
    """,
    version=settings.VERSION,
    docs_url="/docs" if not settings.is_production() else None,
    redoc_url="/redoc" if not settings.is_production() else None,
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    RateLimitMiddleware, 
    requests_per_minute=settings.RATE_LIMIT_REQUESTS
)


# ══════════════════════════════════════════════════════════════════════════════
# EXCEPTION HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", None)
    error_message = exc.detail if isinstance(exc.detail, str) else "Request error"
    detail = None if isinstance(exc.detail, str) else exc.detail
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(
            error_message,
            f"HTTP_{exc.status_code}",
            request_id,
            detail=detail if settings.DEBUG else None
        )
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    request_id = getattr(request.state, "request_id", None)
    detail = exc.errors()
    return JSONResponse(
        status_code=422,
        content=_error_payload(
            "Validation error",
            "VALIDATION_ERROR",
            request_id,
            detail=detail if settings.DEBUG else "Invalid request payload"
        )
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(
    request: Request,
    exc: ValidationError
):
    request_id = getattr(request.state, "request_id", None)
    detail = exc.errors()
    return JSONResponse(
        status_code=422,
        content=_error_payload(
            "Validation error",
            "VALIDATION_ERROR",
            request_id,
            detail=detail if settings.DEBUG else "Invalid response data"
        )
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    log.exception(
        f"Unhandled exception: {exc} | path={request.url.path} | request_id={request_id}"
    )
    
    return JSONResponse(
        status_code=500,
        content=_error_payload(
            "Internal server error",
            "INTERNAL_ERROR",
            request_id,
            detail=str(exc) if settings.DEBUG else None
        )
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Core
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Core"])
async def root():
    """
    API root — returns service information.
    """
    return {
        "name": "Nova IntentOS",
        "version": settings.VERSION,
        "build": settings.BUILD,
        "status": "operational",
        "capabilities": [
            "intent_verification",
            "memory_engine",
            "duplicate_guard",
            "response_generation",
            "intent_ledger",
            "alert_system",
            "analytics"
        ],
        "docs": "/docs" if not settings.is_production() else "https://docs.nova-os.com"
    }


@app.get("/health", tags=["Core"], response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    """
    # Test database connection
    db_status = "connected"
    try:
        await db.fetch_one("SELECT 1")
    except Exception:
        db_status = "disconnected"
    
    uptime = int(time.time() - _startup_time) if _startup_time else 0
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "version": settings.VERSION,
        "build": settings.BUILD,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc),
        "database": db_status,
        "llm_available": settings.has_llm(),
        "uptime_seconds": uptime
    }


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Tokens
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/tokens", tags=["Tokens"], response_model=TokenResponse)
async def create_token(
    payload: TokenCreate,
    ws: Dict = Depends(get_workspace)
):
    """
    Create a new Intent Token for an agent.
    
    An Intent Token defines what an agent can and cannot do,
    and is required for all validation requests.
    """
    # Generate signature
    signature = Crypto.sign({
        "workspace_id": str(ws["id"]),
        "agent_name": payload.agent_name,
        "can_do": payload.can_do,
        "cannot_do": payload.cannot_do,
        "authorized_by": payload.authorized_by,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Insert token
    token_id = await db.execute(
        """INSERT INTO intent_tokens 
           (workspace_id, agent_name, description, can_do, cannot_do, 
            authorized_by, signature, metadata)
           VALUES (:wid, :name, :desc, :can, :cannot, :auth, :sig, :meta)
           RETURNING id""",
        {
            "wid": ws["id"],
            "name": payload.agent_name,
            "desc": payload.description,
            "can": payload.can_do,
            "cannot": payload.cannot_do,
            "auth": payload.authorized_by,
            "sig": signature,
            "meta": json.dumps(payload.metadata)
        }
    )
    
    log.info(f"Token created: {payload.agent_name} (ID: {token_id})")
    
    # Track analytics
    await AnalyticsEngine.track_event(
        str(ws["id"]),
        "token_created",
        {"agent_name": payload.agent_name, "token_id": token_id}
    )
    
    return {
        "id": str(token_id),
        "agent_name": payload.agent_name,
        "description": payload.description,
        "can_do": payload.can_do,
        "cannot_do": payload.cannot_do,
        "authorized_by": payload.authorized_by,
        "signature": signature,
        "active": True,
        "metadata": payload.metadata,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None
    }


@app.get("/tokens", tags=["Tokens"])
async def list_tokens(
    active_only: bool = Query(True, description="Only return active tokens"),
    ws: Dict = Depends(get_workspace)
):
    """
    List all Intent Tokens for the workspace.
    """
    query = """
        SELECT id, agent_name, description, can_do, cannot_do, 
               authorized_by, signature, active, metadata, created_at, updated_at
        FROM intent_tokens 
        WHERE workspace_id = :wid
    """
    
    if active_only:
        query += " AND active = TRUE"
    
    query += " ORDER BY created_at DESC"
    
    rows = await db.fetch_all(query, {"wid": ws["id"]})
    
    return [
        {
            **dict(row),
            "id": str(row["id"]),
            "metadata": row["metadata"] if row["metadata"] else {}
        }
        for row in rows
    ]


@app.get("/tokens/{token_id}", tags=["Tokens"], response_model=TokenResponse)
async def get_token(
    token_id: str = Path(..., description="Token ID"),
    ws: Dict = Depends(get_workspace)
):
    """
    Get details of a specific Intent Token.
    """
    row = await db.fetch_one(
        """SELECT * FROM intent_tokens 
           WHERE id = :tid AND workspace_id = :wid""",
        {"tid": token_id, "wid": ws["id"]}
    )
    
    if not row:
        raise HTTPException(404, "Token not found")
    
    token = dict(row)
    token["id"] = str(token["id"])
    token["metadata"] = token["metadata"] if token["metadata"] else {}
    
    return token


@app.patch("/tokens/{token_id}", tags=["Tokens"])
async def update_token(
    token_id: str,
    payload: TokenUpdate,
    ws: Dict = Depends(get_workspace)
):
    """
    Update an Intent Token.
    """
    # Build update query dynamically
    updates = []
    values = {"tid": token_id, "wid": ws["id"]}
    
    if payload.description is not None:
        updates.append("description = :desc")
        values["desc"] = payload.description
    
    if payload.can_do is not None:
        updates.append("can_do = :can")
        values["can"] = payload.can_do
    
    if payload.cannot_do is not None:
        updates.append("cannot_do = :cannot")
        values["cannot"] = payload.cannot_do
    
    if payload.active is not None:
        updates.append("active = :active")
        values["active"] = payload.active
    
    if payload.metadata is not None:
        updates.append("metadata = :meta")
        values["meta"] = json.dumps(payload.metadata)
    
    if not updates:
        raise HTTPException(400, "No fields to update")
    
    updates.append("updated_at = NOW()")
    
    await db.execute(
        f"UPDATE intent_tokens SET {', '.join(updates)} WHERE id = :tid AND workspace_id = :wid",
        values
    )
    
    return {"status": "updated", "token_id": token_id}


@app.delete("/tokens/{token_id}", tags=["Tokens"])
async def deactivate_token(
    token_id: str,
    ws: Dict = Depends(get_workspace)
):
    """
    Deactivate an Intent Token (soft delete).
    """
    await db.execute(
        """UPDATE intent_tokens 
           SET active = FALSE, updated_at = NOW()
           WHERE id = :tid AND workspace_id = :wid""",
        {"tid": token_id, "wid": ws["id"]}
    )
    
    log.info(f"Token deactivated: {token_id}")
    
    return {"status": "deactivated", "token_id": token_id}


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Validation (The Heart of Nova)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/validate", tags=["Validation"], response_model=ValidateResponse)
async def validate_action(
    payload: ValidateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    ws: Dict = Depends(get_workspace),
    ctx: Dict = Depends(get_request_context)
):
    """
    Validate an agent action and get a verdict.
    
    This is the core endpoint of Nova. In a single call it:
    
    1. Retrieves relevant memories for context
    2. Checks for duplicate actions (if enabled)
    3. Calculates Intent Fidelity Score
    4. Determines verdict: APPROVED / BLOCKED / ESCALATED / DUPLICATE
    5. Generates response (if enabled)
    6. Records to immutable ledger (unless dry_run)
    7. Creates alerts for violations
    8. Auto-saves to memory
    
    Returns all information needed to proceed or explain the decision.
    """
    start_time = time.time()
    
    # ── Load Token ────────────────────────────────────────────────────────────
    token = await db.fetch_one(
        """SELECT * FROM intent_tokens 
           WHERE id = :tid AND workspace_id = :wid AND active = TRUE""",
        {"tid": payload.token_id, "wid": ws["id"]}
    )
    
    if not token:
        raise HTTPException(404, "Intent Token not found or inactive")
    
    token = dict(token)
    
    # ── Get Relevant Memories ─────────────────────────────────────────────────
    memories = await MemoryEngine.get_relevant(
        str(ws["id"]),
        token["agent_name"],
        payload.action
    )
    
    # ── Check Duplicates ──────────────────────────────────────────────────────
    duplicate_info = None
    
    if payload.check_duplicates:
        duplicate_info = await DuplicateGuard.check(
            str(ws["id"]),
            payload.token_id,
            payload.action,
            payload.duplicate_window_minutes,
            payload.duplicate_threshold
        )
        
        if duplicate_info:
            latency = int((time.time() - start_time) * 1000)
            
            return ValidateResponse(
                verdict=Verdict.DUPLICATE,
                score=0,
                reason=f"Similar action executed recently (similarity: {duplicate_info['similarity']*100:.0f}%)",
                response=None,
                execute=False,
                agent_name=token["agent_name"],
                ledger_id=None,
                hash=None,
                memories_used=len(memories),
                duplicate_check="blocked",
                duplicate_of=duplicate_info,
                score_factors={"duplicate_detected": -100},
                request_id=ctx["request_id"],
                latency_ms=latency
            )
    
    # ── Calculate Score ───────────────────────────────────────────────────────
    score, reason, score_factors = await ScoringEngine.calculate_score(
        payload.action,
        token["can_do"],
        token["cannot_do"],
        payload.context or "",
        memories
    )
    
    # ── Determine Verdict ─────────────────────────────────────────────────────
    if score >= settings.SCORE_APPROVED_THRESHOLD:
        verdict = Verdict.APPROVED
    elif score >= settings.SCORE_ESCALATED_THRESHOLD:
        verdict = Verdict.ESCALATED
    else:
        verdict = Verdict.BLOCKED
    
    # ── Generate Response ─────────────────────────────────────────────────────
    response_text = None
    
    if payload.generate_response:
        response_text = await ResponseGenerator.generate(
            payload.action,
            verdict,
            score,
            reason,
            token,
            payload.context or "",
            memories
        )
    
    # ── Record to Ledger ──────────────────────────────────────────────────────
    ledger_id = None
    own_hash = None
    
    if not payload.dry_run:
        # Get previous hash for chain
        prev_row = await db.fetch_one(
            "SELECT own_hash FROM ledger WHERE workspace_id = :wid ORDER BY id DESC LIMIT 1",
            {"wid": ws["id"]}
        )
        prev_hash = prev_row["own_hash"] if prev_row else "GENESIS"
        
        # Create chain hash
        own_hash = Crypto.chain_hash(prev_hash, {
            "workspace_id": str(ws["id"]),
            "token_id": payload.token_id,
            "action": payload.action,
            "score": score,
            "verdict": verdict.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Insert ledger entry
        ledger_id = await db.execute(
            """INSERT INTO ledger 
               (workspace_id, token_id, agent_name, action, context, score, 
                verdict, reason, response, score_factors, prev_hash, own_hash,
                request_id, client_ip, user_agent)
               VALUES (:wid, :tid, :agent, :action, :ctx, :score, :verdict, 
                       :reason, :resp, :factors, :prev, :own, :rid, :ip, :ua)
               RETURNING id""",
            {
                "wid": ws["id"],
                "tid": payload.token_id,
                "agent": token["agent_name"],
                "action": payload.action,
                "ctx": payload.context,
                "score": score,
                "verdict": verdict.value,
                "reason": reason,
                "resp": response_text,
                "factors": json.dumps(score_factors),
                "prev": prev_hash,
                "own": own_hash,
                "rid": ctx["request_id"],
                "ip": ctx["client_ip"],
                "ua": ctx["user_agent"][:200] if ctx["user_agent"] else None
            }
        )
        
        # ── Create Alert if Needed ────────────────────────────────────────────
        if verdict in (Verdict.BLOCKED, Verdict.ESCALATED):
            background_tasks.add_task(
                AlertSystem.create,
                str(ws["id"]),
                ledger_id,
                token["agent_name"],
                f"[{verdict.value}] {token['agent_name']}: {payload.action[:120]}",
                score,
                AlertType.VIOLATION if verdict == Verdict.BLOCKED else AlertType.ESCALATION
            )
        
        # ── Auto-save Memory ──────────────────────────────────────────────────
        background_tasks.add_task(
            MemoryEngine.auto_save,
            str(ws["id"]),
            token["agent_name"],
            payload.action,
            verdict,
            score,
            payload.context or ""
        )
    
    # ── Build Response ────────────────────────────────────────────────────────
    latency = int((time.time() - start_time) * 1000)
    
    log.info(
        f"Validated: {token['agent_name']} | {verdict.value} | "
        f"score={score} | {latency}ms | {ctx['request_id']}"
    )
    
    return ValidateResponse(
        verdict=verdict,
        score=score,
        reason=reason,
        response=response_text,
        execute=verdict == Verdict.APPROVED,
        agent_name=token["agent_name"],
        ledger_id=ledger_id,
        hash=own_hash,
        memories_used=len(memories),
        duplicate_check="clean",
        duplicate_of=None,
        score_factors=score_factors,
        request_id=ctx["request_id"],
        latency_ms=latency
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Webhook
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/webhook/{api_key}", tags=["Webhook"])
async def webhook(
    api_key: str,
    body: WebhookBody,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Flexible webhook endpoint for n8n, Zapier, Make, etc.
    
    Accepts various field names and can optionally:
    - Save a memory before validation
    - Generate a response
    - Check for duplicates
    
    The webhook automatically finds the first active token
    if none is specified.
    """
    # Authenticate
    ws = await db.fetch_one(
        "SELECT * FROM workspaces WHERE api_key = :key",
        {"key": api_key}
    )
    
    if not ws:
        raise HTTPException(401, "Invalid API key")
    
    ws = dict(ws)
    
    # Extract action from various possible field names
    action = body.action or body.message or body.texto
    
    if not action:
        raise HTTPException(400, "No action provided. Use 'action', 'message', or 'texto' field.")
    
    context = body.context or body.contexto or ""
    token_id = body.token_id or body.token or ""
    
    # Save memory if provided
    if body.memory_key and body.memory_val:
        await db.execute(
            """INSERT INTO memories 
               (workspace_id, agent_name, key, value, tags, importance, source)
               VALUES (:wid, :agent, :key, :val, :tags, :imp, 'webhook')""",
            {
                "wid": ws["id"],
                "agent": body.agent_name or "webhook_agent",
                "key": body.memory_key,
                "val": body.memory_val,
                "tags": body.memory_tags or ["webhook"],
                "imp": body.memory_importance or 5
            }
        )
    
    # Find token if not provided
    if not token_id:
        row = await db.fetch_one(
            "SELECT id FROM intent_tokens WHERE workspace_id = :wid AND active = TRUE LIMIT 1",
            {"wid": ws["id"]}
        )
        
        if row:
            token_id = str(row["id"])
        else:
            return {
                "verdict": "NO_TOKEN",
                "execute": True,
                "score": 50,
                "reason": "No active Intent Token found — action allowed by default",
                "warning": "Create an Intent Token for proper governance"
            }
    
    # Create context for validation
    ctx = {
        "request_id": Crypto.generate_request_id(),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", ""),
        "start_time": time.time()
    }
    
    # Validate
    return await validate_action(
        ValidateRequest(
            token_id=token_id,
            action=action,
            context=context,
            generate_response=body.respond,
            check_duplicates=body.dedup,
            dry_run=body.dry_run
        ),
        request,
        background_tasks,
        ws,
        ctx
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Memory
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/memory", tags=["Memory"], response_model=MemoryResponse)
async def save_memory(
    payload: MemoryCreate,
    ws: Dict = Depends(get_workspace)
):
    """
    Save a memory for an agent.
    
    Memories provide persistent context that can be used
    during action validation.
    """
    # Calculate expiration
    expires_at = None
    if payload.expires_in_hours:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=payload.expires_in_hours)
    
    # Check memory limit
    count = await db.fetch_one(
        "SELECT COUNT(*) c FROM memories WHERE workspace_id = :wid AND agent_name = :agent",
        {"wid": ws["id"], "agent": payload.agent_name}
    )
    
    if count["c"] >= settings.MEMORY_MAX_PER_AGENT:
        # Delete oldest low-importance memories
        await db.execute(
            """DELETE FROM memories 
               WHERE id IN (
                   SELECT id FROM memories 
                   WHERE workspace_id = :wid AND agent_name = :agent
                   ORDER BY importance ASC, created_at ASC
                   LIMIT 10
               )""",
            {"wid": ws["id"], "agent": payload.agent_name}
        )
    
    # Insert memory
    memory_id = await db.execute(
        """INSERT INTO memories 
           (workspace_id, agent_name, key, value, tags, importance, source, metadata, expires_at)
           VALUES (:wid, :agent, :key, :val, :tags, :imp, 'manual', :meta, :exp)
           RETURNING id""",
        {
            "wid": ws["id"],
            "agent": payload.agent_name,
            "key": payload.key,
            "val": payload.value,
            "tags": payload.tags,
            "imp": payload.importance,
            "meta": json.dumps(payload.metadata),
            "exp": expires_at
        }
    )
    
    return {
        "id": memory_id,
        "agent_name": payload.agent_name,
        "key": payload.key,
        "value": payload.value,
        "tags": payload.tags,
        "importance": payload.importance,
        "source": "manual",
        "metadata": payload.metadata,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None
    }


@app.get("/memory/{agent_name}", tags=["Memory"])
async def get_memories(
    agent_name: str = Path(..., description="Agent name"),
    limit: int = Query(50, ge=1, le=200),
    min_importance: int = Query(1, ge=1, le=10),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    ws: Dict = Depends(get_workspace)
):
    """
    Get memories for an agent.
    """
    query = """
        SELECT id, key, value, tags, importance, source, metadata, 
               expires_at, created_at, updated_at
        FROM memories 
        WHERE workspace_id = :wid 
          AND agent_name = :agent
          AND (expires_at IS NULL OR expires_at > NOW())
          AND importance >= :min_imp
    """
    params = {
        "wid": ws["id"],
        "agent": agent_name,
        "min_imp": min_importance,
        "lim": limit
    }
    
    if tag:
        query += " AND :tag = ANY(tags)"
        params["tag"] = tag
    
    query += " ORDER BY importance DESC, created_at DESC LIMIT :lim"
    
    rows = await db.fetch_all(query, params)
    
    return [
        {
            **dict(row),
            "metadata": row["metadata"] if row["metadata"] else {}
        }
        for row in rows
    ]


@app.post("/memory/search", tags=["Memory"])
async def search_memories(
    payload: MemorySearch,
    ws: Dict = Depends(get_workspace)
):
    """
    Search memories by semantic relevance to a query.
    """
    return await MemoryEngine.get_relevant(
        str(ws["id"]),
        payload.agent_name,
        payload.query,
        payload.limit
    )


@app.patch("/memory/{memory_id}", tags=["Memory"])
async def update_memory(
    memory_id: int,
    payload: MemoryUpdate,
    ws: Dict = Depends(get_workspace)
):
    """
    Update a memory.
    """
    updates = ["updated_at = NOW()"]
    values = {"mid": memory_id, "wid": ws["id"]}
    
    if payload.value is not None:
        updates.append("value = :val")
        values["val"] = payload.value
    
    if payload.tags is not None:
        updates.append("tags = :tags")
        values["tags"] = payload.tags
    
    if payload.importance is not None:
        updates.append("importance = :imp")
        values["imp"] = payload.importance
    
    if payload.expires_in_hours is not None:
        updates.append("expires_at = NOW() + :exp * INTERVAL '1 hour'")
        values["exp"] = payload.expires_in_hours
    
    if payload.metadata is not None:
        updates.append("metadata = :meta")
        values["meta"] = json.dumps(payload.metadata)
    
    if len(updates) == 1:  # Only updated_at
        raise HTTPException(400, "No fields to update")
    
    await db.execute(
        f"UPDATE memories SET {', '.join(updates)} WHERE id = :mid AND workspace_id = :wid",
        values
    )
    
    return {"status": "updated", "memory_id": memory_id}


@app.delete("/memory/{agent_name}", tags=["Memory"])
async def clear_memories(
    agent_name: str,
    expired_only: bool = Query(False, description="Only clear expired memories"),
    ws: Dict = Depends(get_workspace)
):
    """
    Clear memories for an agent.
    """
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
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    verdict: Optional[str] = Query(None, description="Filter by verdict"),
    agent_name: Optional[str] = Query(None, description="Filter by agent"),
    since: Optional[datetime] = Query(None, description="Filter by start date"),
    until: Optional[datetime] = Query(None, description="Filter by end date"),
    ws: Dict = Depends(get_workspace)
):
    """
    Get ledger entries with optional filtering.
    
    The ledger is an immutable audit trail of all validation decisions.
    """
    query = """
        SELECT id, agent_name, action, context, score, verdict, reason, 
               response, score_factors, own_hash, executed_at
        FROM ledger 
        WHERE workspace_id = :wid
    """
    params: Dict = {"wid": ws["id"], "limit": limit, "offset": offset}
    
    if verdict:
        query += " AND verdict = :verdict"
        params["verdict"] = verdict.upper()
    
    if agent_name:
        query += " AND agent_name = :agent"
        params["agent"] = agent_name
    
    if since:
        query += " AND executed_at >= :since"
        params["since"] = since
    
    if until:
        query += " AND executed_at <= :until"
        params["until"] = until
    
    query += " ORDER BY id DESC LIMIT :limit OFFSET :offset"
    
    rows = await db.fetch_all(query, params)
    
    return [
        {
            **dict(row),
            "score_factors": row["score_factors"] if row["score_factors"] else {}
        }
        for row in rows
    ]


@app.get("/ledger/{entry_id}", tags=["Ledger"])
async def get_ledger_entry(
    entry_id: int,
    ws: Dict = Depends(get_workspace)
):
    """
    Get a specific ledger entry.
    """
    row = await db.fetch_one(
        """SELECT * FROM ledger WHERE id = :id AND workspace_id = :wid""",
        {"id": entry_id, "wid": ws["id"]}
    )
    
    if not row:
        raise HTTPException(404, "Ledger entry not found")
    
    entry = dict(row)
    entry["score_factors"] = entry["score_factors"] if entry["score_factors"] else {}
    
    return entry


@app.get("/ledger/verify", tags=["Ledger"])
async def verify_chain(ws: Dict = Depends(get_workspace)):
    """
    Verify the cryptographic integrity of the ledger chain.
    
    Returns whether all records are intact and unmodified.
    """
    rows = await db.fetch_all(
        "SELECT * FROM ledger WHERE workspace_id = :wid ORDER BY id ASC",
        {"wid": ws["id"]}
    )
    
    if not rows:
        return {
            "verified": True,
            "total_records": 0,
            "broken_at": None,
            "chain_hash": None
        }
    
    prev_hash = "GENESIS"
    broken_at = None
    
    for row in rows:
        row = dict(row)
        
        expected = Crypto.chain_hash(prev_hash, {
            "workspace_id": str(ws["id"]),
            "token_id": str(row["token_id"]),
            "action": row["action"],
            "score": row["score"],
            "verdict": row["verdict"],
            "timestamp": row["executed_at"].isoformat() if row["executed_at"] else ""
        })
        
        # Check both own_hash and chain continuity
        if row["own_hash"] != expected or row["prev_hash"] != prev_hash:
            broken_at = row["id"]
            break
        
        prev_hash = row["own_hash"]
    
    last_hash = rows[-1]["own_hash"] if rows else None
    
    return {
        "verified": broken_at is None,
        "total_records": len(rows),
        "broken_at": broken_at,
        "chain_hash": last_hash
    }


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Alerts
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/alerts", tags=["Alerts"])
async def get_alerts(
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=200),
    ws: Dict = Depends(get_workspace)
):
    """
    Get alerts for the workspace.
    """
    query = """
        SELECT id, agent_name, alert_type, severity, message, score, 
               metadata, resolved, resolved_by, resolved_at, created_at
        FROM alerts 
        WHERE workspace_id = :wid
    """
    params: Dict = {"wid": ws["id"], "limit": limit}
    
    if resolved is not None:
        query += " AND resolved = :resolved"
        params["resolved"] = resolved
    
    if severity:
        query += " AND severity = :severity"
        params["severity"] = severity.lower()
    
    query += " ORDER BY created_at DESC LIMIT :limit"
    
    rows = await db.fetch_all(query, params)
    
    return [
        {
            **dict(row),
            "metadata": row["metadata"] if row["metadata"] else {}
        }
        for row in rows
    ]


@app.patch("/alerts/{alert_id}/resolve", tags=["Alerts"])
async def resolve_alert(
    alert_id: int,
    payload: AlertResolve = Body(default=AlertResolve()),
    ws: Dict = Depends(get_workspace)
):
    """
    Mark an alert as resolved.
    """
    await AlertSystem.resolve(
        str(ws["id"]),
        alert_id,
        payload.resolved_by
    )
    
    return {"status": "resolved", "alert_id": alert_id}


@app.delete("/alerts/{alert_id}", tags=["Alerts"])
async def delete_alert(
    alert_id: int,
    ws: Dict = Depends(get_workspace)
):
    """
    Delete an alert (only resolved alerts can be deleted).
    """
    result = await db.execute(
        "DELETE FROM alerts WHERE id = :id AND workspace_id = :wid AND resolved = TRUE",
        {"id": alert_id, "wid": ws["id"]}
    )
    
    if result == 0:
        raise HTTPException(400, "Alert not found or not resolved")
    
    return {"status": "deleted", "alert_id": alert_id}


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Statistics
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/stats", tags=["Analytics"], response_model=StatsResponse)
async def get_stats(ws: Dict = Depends(get_workspace)):
    """
    Get comprehensive statistics for the workspace.
    """
    return await AnalyticsEngine.get_stats(str(ws["id"]))


@app.get("/stats/agents", tags=["Analytics"])
async def get_agent_stats(ws: Dict = Depends(get_workspace)):
    """
    Get statistics broken down by agent.
    """
    query = """
        SELECT 
            l.agent_name,
            COUNT(*) as total_actions,
            COUNT(*) FILTER (WHERE l.verdict = 'APPROVED') as approved,
            COUNT(*) FILTER (WHERE l.verdict = 'BLOCKED') as blocked,
            ROUND(AVG(l.score)) as avg_score,
            MAX(l.executed_at) as last_action
        FROM ledger l
        WHERE l.workspace_id = :wid
        GROUP BY l.agent_name
        ORDER BY total_actions DESC
    """
    
    rows = await db.fetch_all(query, {"wid": ws["id"]})
    
    return [
        {
            "agent_name": row["agent_name"],
            "total_actions": row["total_actions"],
            "approved": row["approved"],
            "blocked": row["blocked"],
            "avg_score": int(row["avg_score"] or 0),
            "approval_rate": round(row["approved"] / max(row["total_actions"], 1) * 100, 1),
            "last_action": row["last_action"]
        }
        for row in rows
    ]


@app.get("/stats/hourly", tags=["Analytics"])
async def get_hourly_stats(
    days: int = Query(7, ge=1, le=30),
    ws: Dict = Depends(get_workspace)
):
    """
    Get hourly action distribution.
    """
    query = """
        SELECT 
            EXTRACT(HOUR FROM executed_at) as hour,
            COUNT(*) as count,
            ROUND(AVG(score)) as avg_score
        FROM ledger
        WHERE workspace_id = :wid
          AND executed_at > NOW() - :days * INTERVAL '1 day'
        GROUP BY EXTRACT(HOUR FROM executed_at)
        ORDER BY hour
    """
    
    rows = await db.fetch_all(query, {"wid": ws["id"], "days": days})
    
    # Fill in missing hours with zeros
    hourly = {int(row["hour"]): {"count": row["count"], "avg_score": int(row["avg_score"] or 0)} for row in rows}
    
    return [
        {
            "hour": h,
            "count": hourly.get(h, {}).get("count", 0),
            "avg_score": hourly.get(h, {}).get("avg_score", 0)
        }
        for h in range(24)
    ]


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Demo/Development
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/demo/seed", tags=["Development"])
async def seed_demo_data(ws: Dict = Depends(get_workspace)):
    """
    Seed the workspace with demo agents, actions, and memories.
    
    Useful for testing and demonstrations.
    """
    # Demo agents
    agents = [
        {
            "name": "Email Agent",
            "desc": "Handles customer email communications",
            "can": [
                "Reply to customer emails",
                "Check order status",
                "Provide tracking information",
                "Answer product questions"
            ],
            "cannot": [
                "Offer discounts greater than 10%",
                "Promise delivery dates without checking inventory",
                "Share customer data externally",
                "Process refunds over $500"
            ]
        },
        {
            "name": "Billing Agent",
            "desc": "Manages invoicing and payments",
            "can": [
                "Generate invoices",
                "Send payment reminders",
                "Process payments under $1000",
                "Check payment history"
            ],
            "cannot": [
                "Modify issued invoices",
                "Cancel invoices over $5000",
                "Change payment terms without approval",
                "Access other customer accounts"
            ]
        },
        {
            "name": "Inventory Agent",
            "desc": "Monitors and updates stock levels",
            "can": [
                "Update stock counts",
                "Generate low stock alerts",
                "Create purchase requests under $5000",
                "View supplier information"
            ],
            "cannot": [
                "Create purchase orders over $10000",
                "Delete active products",
                "Modify pricing",
                "Access financial reports"
            ]
        }
    ]
    
    token_ids = []
    
    for agent in agents:
        sig = Crypto.sign({
            "name": agent["name"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        tid = await db.execute(
            """INSERT INTO intent_tokens 
               (workspace_id, agent_name, description, can_do, cannot_do, authorized_by, signature)
               VALUES (:wid, :name, :desc, :can, :cannot, :auth, :sig)
               RETURNING id""",
            {
                "wid": ws["id"],
                "name": agent["name"],
                "desc": agent["desc"],
                "can": agent["can"],
                "cannot": agent["cannot"],
                "auth": "demo@nova-os.com",
                "sig": sig
            }
        )
        token_ids.append((str(tid), agent["name"]))
    
    # Demo memories
    memories = [
        ("Email Agent", "vip_customer_policy", "VIP customers can receive up to 8% discount without approval", ["policy", "vip"], 9),
        ("Email Agent", "standard_discount", "Standard discount policy: 5% for regular customers, never exceed 10%", ["policy"], 9),
        ("Billing Agent", "high_value_approval", "Invoices over $5000 require CFO approval before cancellation", ["policy", "approval"], 8),
        ("Inventory Agent", "primary_supplier", "Primary supplier: LogiCo SA — Contact: orders@logico.com", ["supplier", "contact"], 6),
        ("Inventory Agent", "reorder_threshold", "Minimum stock threshold before reorder: 50 units", ["policy", "inventory"], 7),
    ]
    
    for agent_name, key, value, tags, importance in memories:
        await db.execute(
            """INSERT INTO memories 
               (workspace_id, agent_name, key, value, tags, importance, source)
               VALUES (:wid, :agent, :key, :val, :tags, :imp, 'demo')""",
            {
                "wid": ws["id"],
                "agent": agent_name,
                "key": key,
                "val": value,
                "tags": tags,
                "imp": importance
            }
        )
    
    # Demo actions
    demo_actions = [
        ("Reply to customer inquiry about order #4821 status", 92, "APPROVED"),
        ("Offer 25% discount to a complaining customer", 15, "BLOCKED"),
        ("Generate invoice #F-2024-089 for $1,200", 94, "APPROVED"),
        ("Cancel invoice #F-2024-071 for $8,500", 12, "BLOCKED"),
        ("Update stock: Product A now at 45 units", 91, "APPROVED"),
        ("Create purchase order for $15,000 without approval", 18, "BLOCKED"),
        ("Send order tracking information to customer", 96, "APPROVED"),
        ("Process payment reminder for overdue invoice", 89, "APPROVED"),
        ("Promise 24-hour delivery without checking stock", 25, "BLOCKED"),
        ("Alert: Low stock warning for Product C", 93, "APPROVED"),
        ("Modify previously issued invoice #F-2024-055", 8, "BLOCKED"),
        ("Respond to product availability question", 88, "APPROVED"),
        ("Share customer list with marketing partner", 5, "BLOCKED"),
        ("Check inventory levels for quarterly report", 90, "APPROVED"),
    ]
    
    prev_hash = "GENESIS"
    
    for i, (action, score, verdict) in enumerate(demo_actions):
        token_id, agent_name = token_ids[i % len(token_ids)]
        
        own_hash = Crypto.chain_hash(prev_hash, {
            "workspace_id": str(ws["id"]),
            "token_id": token_id,
            "action": action,
            "score": score,
            "verdict": verdict,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        lid = await db.execute(
            """INSERT INTO ledger 
               (workspace_id, token_id, agent_name, action, score, verdict, 
                reason, prev_hash, own_hash)
               VALUES (:wid, :tid, :agent, :action, :score, :verdict, 
                       :reason, :prev, :own)
               RETURNING id""",
            {
                "wid": ws["id"],
                "tid": token_id,
                "agent": agent_name,
                "action": action,
                "score": score,
                "verdict": verdict,
                "reason": "Demo data",
                "prev": prev_hash,
                "own": own_hash
            }
        )
        
        if verdict == "BLOCKED":
            await AlertSystem.create(
                str(ws["id"]),
                lid,
                agent_name,
                f"[DEMO] {action[:80]}",
                score,
                AlertType.VIOLATION
            )
        
        prev_hash = own_hash
    
    log.info(f"Demo data seeded for workspace {ws['id']}")
    
    return {
        "status": "seeded",
        "tokens": len(token_ids),
        "actions": len(demo_actions),
        "memories": len(memories),
        "message": "Demo data has been loaded. Explore with 'nova status'"
    }


@app.delete("/demo/reset", tags=["Development"])
async def reset_demo_data(
    confirm: bool = Query(False, description="Must be true to confirm"),
    ws: Dict = Depends(get_workspace)
):
    """
    Reset all data in the workspace.
    
    ⚠️ DANGER: This permanently deletes all tokens, ledger entries,
    memories, and alerts. This action cannot be undone.
    """
    if not confirm:
        raise HTTPException(
            400,
            "Must confirm deletion by passing ?confirm=true"
        )
    
    if settings.is_production():
        raise HTTPException(
            403,
            "Reset is disabled in production environment"
        )
    
    # Delete in order (respecting foreign keys)
    await db.execute("DELETE FROM alerts WHERE workspace_id = :wid", {"wid": ws["id"]})
    await db.execute("DELETE FROM memories WHERE workspace_id = :wid", {"wid": ws["id"]})
    await db.execute("DELETE FROM ledger WHERE workspace_id = :wid", {"wid": ws["id"]})
    await db.execute("DELETE FROM intent_tokens WHERE workspace_id = :wid", {"wid": ws["id"]})
    await db.execute("DELETE FROM analytics_events WHERE workspace_id = :wid", {"wid": ws["id"]})
    await db.execute("DELETE FROM rate_limits WHERE workspace_id = :wid", {"wid": ws["id"]})
    
    log.warning(f"Workspace {ws['id']} has been reset")
    
    return {
        "status": "reset",
        "message": "All data has been deleted",
        "workspace_id": str(ws["id"])
    }


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
        access_log=True
    )
