"""Centralized configuration loading for Nova OS."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    _HAS_PYDANTIC_SETTINGS = True
except ImportError:  # pragma: no cover - host compatibility fallback
    from pydantic import BaseModel

    _HAS_PYDANTIC_SETTINGS = False

    class SettingsConfigDict(dict[str, Any]):
        """Fallback shim used when pydantic-settings is unavailable."""

    class BaseSettings(BaseModel):
        """Minimal BaseSettings-compatible fallback."""

from nova.constants import NOVA_VERSION


class NovaConfig(BaseSettings):
    """Environment-driven configuration for the Nova kernel."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    env: str = Field(default="development", alias="NOVA_ENV")
    version: str = Field(default=NOVA_VERSION, alias="NOVA_VERSION")
    host: str = Field(default="0.0.0.0", alias="NOVA_HOST")
    api_port: int = Field(default=9800, alias="NOVA_API_PORT")
    bridge_port: int = Field(default=9700, alias="NOVA_BRIDGE_PORT")
    log_level: str = Field(default="INFO", alias="NOVA_LOG_LEVEL")
    log_format: str = Field(default="json", alias="NOVA_LOG_FORMAT")

    db_url: str = Field(default="sqlite+aiosqlite:///./nova.db", alias="NOVA_DB_URL")
    workspace_root: Path = Field(default=Path("."), alias="NOVA_WORKSPACE_ROOT")
    data_dir: Path = Field(default=Path("./data"), alias="NOVA_DATA_DIR")

    jwt_secret: str = Field(default="change-me", alias="NOVA_JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="NOVA_JWT_ALGORITHM")
    jwt_expiry_hours: int = Field(default=24, alias="NOVA_JWT_EXPIRY_HOURS")
    api_key_prefix: str = Field(default="nova_", alias="NOVA_API_KEY_PREFIX")

    auto_allow_threshold: int = Field(default=30, alias="NOVA_RISK_AUTO_ALLOW_THRESHOLD")
    escalate_threshold: int = Field(default=60, alias="NOVA_RISK_ESCALATE_THRESHOLD")
    auto_block_threshold: int = Field(default=80, alias="NOVA_RISK_AUTO_BLOCK_THRESHOLD")

    rate_limit_per_minute: int = Field(default=100, alias="NOVA_RATE_LIMIT_PER_MINUTE")
    rate_limit_burst: int = Field(default=20, alias="NOVA_RATE_LIMIT_BURST")

    anomaly_burst_threshold: int = Field(default=50, alias="NOVA_ANOMALY_BURST_THRESHOLD")
    anomaly_loop_similarity: float = Field(default=0.85, alias="NOVA_ANOMALY_LOOP_SIMILARITY")
    anomaly_check_interval: int = Field(default=30, alias="NOVA_ANOMALY_CHECK_INTERVAL")
    discovery_enabled: bool = Field(default=True, alias="NOVA_DISCOVERY_ENABLED")
    discovery_scan_ttl_seconds: int = Field(default=60, alias="NOVA_DISCOVERY_SCAN_TTL")
    discovery_watch_interval_seconds: int = Field(default=60, alias="NOVA_DISCOVERY_WATCH_INTERVAL")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    xai_api_key: str = Field(default="", alias="XAI_API_KEY")
    mistral_api_key: str = Field(default="", alias="MISTRAL_API_KEY")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    cohere_api_key: str = Field(default="", alias="COHERE_API_KEY")

    health_check_interval_seconds: int = 30
    episodic_ttl_hours: int = 72
    working_memory_limit: int = 200
    http_timeout_seconds: float = 30.0

    def __init__(self, **data: Any) -> None:
        if not _HAS_PYDANTIC_SETTINGS:
            merged = {**self._fallback_env_values(), **data}
            super().__init__(**merged)
            return
        super().__init__(**data)

    @classmethod
    def _fallback_env_values(cls) -> dict[str, Any]:
        """Load environment values, including a local `.env`, without pydantic-settings."""

        values: dict[str, Any] = {}
        dotenv_values = cls._read_dotenv(Path(".env"))
        for field_name, field_info in cls.model_fields.items():
            alias = field_info.alias or field_name
            if alias in os.environ:
                values[field_name] = os.environ[alias]
            elif alias in dotenv_values:
                values[field_name] = dotenv_values[alias]
        return values

    @staticmethod
    def _read_dotenv(path: Path) -> dict[str, str]:
        """Parse a simple dotenv file."""

        if not path.exists():
            return {}
        values: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, raw_value = stripped.split("=", 1)
            values[key.strip()] = raw_value.strip().strip("'\"")
        return values

    def provider_keys(self) -> dict[str, str]:
        """Return provider API keys in a normalized mapping."""

        return {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "gemini": self.google_api_key,
            "groq": self.groq_api_key,
            "openrouter": self.openrouter_api_key,
            "xai": self.xai_api_key,
            "mistral": self.mistral_api_key,
            "deepseek": self.deepseek_api_key,
            "cohere": self.cohere_api_key,
        }

    def ensure_directories(self) -> None:
        """Create runtime directories used by the kernel."""

        self.data_dir.mkdir(parents=True, exist_ok=True)

    def public_dict(self) -> dict[str, Any]:
        """Return a redacted config snapshot safe for logs or status endpoints."""

        return {
            "env": self.env,
            "version": self.version,
            "host": self.host,
            "api_port": self.api_port,
            "bridge_port": self.bridge_port,
            "db_url": self.db_url,
            "thresholds": {
                "auto_allow": self.auto_allow_threshold,
                "escalate": self.escalate_threshold,
                "auto_block": self.auto_block_threshold,
            },
        }
