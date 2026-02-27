"""
@file security.py
@brief JWT creation / validation and password hashing utilities.

Centralizes all cryptographic operations so that route handlers and services
never interact with low-level token or hash details directly.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
import structlog
from jose import JWTError, jwt

from app.core.config import Settings, get_settings
from app.core.i18n import _

logger = structlog.get_logger(__name__)


def hash_password(plain: str) -> str:
    """
    @brief Hash a plaintext password using bcrypt.

    @param plain The plaintext password.
    @return Bcrypt hash string.
    """
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    @brief Verify a plaintext password against a bcrypt hash.

    @param plain The plaintext password to check.
    @param hashed The stored bcrypt hash.
    @return True if the password matches, False otherwise.
    """
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(
    subject: UUID | str,
    extra_claims: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> str:
    """
    @brief Create a short-lived JWT access token.

    @param subject User ID (UUID) to embed as the ``sub`` claim.
    @param extra_claims Optional additional claims (e.g. role).
    @param settings Override settings for testing.
    @return Encoded JWT string.
    """
    s = settings or get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=s.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, s.SECRET_KEY, algorithm=s.JWT_ALGORITHM)


def create_refresh_token(
    subject: UUID | str,
    settings: Settings | None = None,
) -> str:
    """
    @brief Create a long-lived JWT refresh token.

    @param subject User ID (UUID) to embed as the ``sub`` claim.
    @param settings Override settings for testing.
    @return Encoded JWT string.
    """
    s = settings or get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(days=s.REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "refresh",
    }
    return jwt.encode(payload, s.SECRET_KEY, algorithm=s.JWT_ALGORITHM)


def decode_token(
    token: str,
    expected_type: str = "access",
    settings: Settings | None = None,
) -> dict[str, Any]:
    """
    @brief Decode and validate a JWT token.

    @param token The encoded JWT string.
    @param expected_type Expected ``type`` claim (``"access"`` or ``"refresh"``).
    @param settings Override settings for testing.
    @return Decoded payload dict.
    @raises ValueError If the token is invalid, expired, or has the wrong type.
    """
    s = settings or get_settings()
    try:
        payload = jwt.decode(token, s.SECRET_KEY, algorithms=[s.JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError(_("Invalid or expired token")) from exc

    if payload.get("type") != expected_type:
        raise ValueError(_("Invalid token type"))

    if "sub" not in payload:
        raise ValueError(_("Token missing subject claim"))

    return payload
