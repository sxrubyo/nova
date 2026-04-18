"""System-wide constants for Nova OS."""

from __future__ import annotations

from typing import Final

NOVA_NAME: Final[str] = "Nova OS"
NOVA_VERSION: Final[str] = "4.0.0"
NOVA_BUILD: Final[str] = "enterprise"

NOVA_ASCII_BANNER: Final[str] = r"""
╔══════════════════════════════════════════════╗
║                                              ║
║                ▄███████                      ║
║            ▄████████████                     ║
║         ▄███████   ██████████                ║
║       ▄███████████████████████               ║
║         ▀████████████████████▀               ║
║          ▄██████████████████▄                ║
║          ▀██████████████████▀                ║
║                                              ║
║         NOVA OS v4.0.0 (Enterprise)          ║
║        AI Governance Control Plane           ║
║                                              ║
╠══════════════════════════════════════════════╣
║  API Server:    http://0.0.0.0:9800          ║
║  Bridge Server: ws://0.0.0.0:9700            ║
║  API Docs:      http://0.0.0.0:9800/api/docs ║
║  Status:        All systems operational ✓    ║
╚══════════════════════════════════════════════╝
"""

DEFAULT_PROVIDER_MODELS: Final[dict[str, list[str]]] = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o3-mini"],
    "anthropic": ["claude-3.5-sonnet", "claude-3-opus", "claude-3-haiku"],
    "gemini": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0"],
    "groq": ["llama-3.1-70b", "mixtral-8x7b"],
    "openrouter": ["openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet"],
    "xai": ["grok-2"],
    "mistral": ["mistral-large", "mistral-medium"],
    "deepseek": ["deepseek-chat", "deepseek-coder"],
    "cohere": ["command-r-plus"],
}

PUBLIC_ENDPOINTS: Final[set[str]] = {
    "/",
    "/api/status",
    "/api/auth/login",
    "/api/auth/register",
    "/api/docs",
    "/api/redoc",
    "/openapi.json",
}
