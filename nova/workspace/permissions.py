"""Authentication, authorization, and password helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    from jose import jwt
except ImportError:  # pragma: no cover - host compatibility fallback
    try:
        import jwt  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover - host compatibility fallback
        jwt = None  # type: ignore[assignment]

try:
    from passlib.context import CryptContext
except ImportError:  # pragma: no cover - host compatibility fallback
    CryptContext = None

from nova.config import NovaConfig

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto") if CryptContext else None
_PBKDF2_ITERATIONS = 390_000


def hash_password(password: str) -> str:
    """Hash a plaintext password."""

    if pwd_context is None:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
        return "pbkdf2_sha256${iterations}${salt}${digest}".format(
            iterations=_PBKDF2_ITERATIONS,
            salt=base64.b64encode(salt).decode("utf-8"),
            digest=base64.b64encode(digest).decode("utf-8"),
        )
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash."""

    if pwd_context is None:
        try:
            algorithm, iterations, encoded_salt, encoded_digest = hashed_password.split("$", 3)
        except ValueError:
            return False
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(encoded_salt.encode("utf-8"))
        expected = base64.b64decode(encoded_digest.encode("utf-8"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    return pwd_context.verify(password, hashed_password)


def create_access_token(config: NovaConfig, subject: str, claims: dict[str, Any]) -> str:
    """Create a signed JWT for API authentication."""

    if jwt is None:
        raise RuntimeError("JWT support requires python-jose or PyJWT to be installed")
    expires_at = datetime.now(timezone.utc) + timedelta(hours=config.jwt_expiry_hours)
    payload = {"sub": subject, "exp": expires_at, **claims}
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


def decode_access_token(config: NovaConfig, token: str) -> dict[str, Any]:
    """Decode and validate a JWT."""

    if jwt is None:
        raise RuntimeError("JWT support requires python-jose or PyJWT to be installed")
    return jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])
