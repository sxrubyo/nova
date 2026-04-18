"""Custom exceptions for Nova OS."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class NovaException(Exception):
    """Base exception with a stable error code."""

    code: str
    message: str
    eval_id: str | None = None

    def __str__(self) -> str:
        return self.message


class ConfigurationError(NovaException):
    """Raised when Nova configuration is invalid."""


class AuthenticationError(NovaException):
    """Raised when authentication fails."""


class AuthorizationError(NovaException):
    """Raised when a caller lacks permission."""


class ResourceNotFoundError(NovaException):
    """Raised when a resource cannot be found."""


class ValidationFailure(NovaException):
    """Raised when validation of a payload fails."""


class AllProvidersFailedError(NovaException):
    """Raised when every provider in a failover chain fails."""
