"""
@file security.py
@brief Cryptographic utilities: JWT (RS256), password hashing, TOTP, backup codes.

Centralizes all cryptographic operations so that route handlers and services
never interact with low-level token or hash details directly.  RS256 key pair
is auto-generated on first use if PEM files are absent.
"""

from __future__ import annotations

import hashlib
import secrets
import string
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import bcrypt
import pyotp
import structlog
from jose import JWTError, jwt
from jose.utils import long_to_base64

from app.core.config import Settings, get_settings
from app.core.i18n import _

logger = structlog.get_logger(__name__)

_private_key: str | None = None
_public_key: str | None = None


def _load_or_generate_rsa_keys(settings: Settings) -> tuple[str, str]:
    """
    @brief Load RSA key pair from PEM files, or generate and persist a new pair.

    @param settings Application settings with key file paths.
    @return Tuple of (private_key_pem, public_key_pem).
    """
    global _private_key, _public_key
    if _private_key and _public_key:
        return _private_key, _public_key

    priv_path = Path(settings.JWT_PRIVATE_KEY_PATH)
    pub_path = Path(settings.JWT_PUBLIC_KEY_PATH)

    if priv_path.exists() and pub_path.exists():
        _private_key = priv_path.read_text()
        _public_key = pub_path.read_text()
        logger.info("jwt_keys_loaded", private_key_path=str(priv_path))
        return _private_key, _public_key

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _private_key = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    _public_key = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )

    priv_path.parent.mkdir(parents=True, exist_ok=True)
    priv_path.write_text(_private_key)
    priv_path.chmod(0o600)
    pub_path.write_text(_public_key)
    logger.info("jwt_keys_generated", private_key_path=str(priv_path))
    return _private_key, _public_key


def _get_signing_key(settings: Settings) -> str:
    """@brief Return the JWT signing key (private RSA or HMAC secret)."""
    if settings.JWT_ALGORITHM.startswith("RS"):
        priv, _ = _load_or_generate_rsa_keys(settings)
        return priv
    return settings.SECRET_KEY


def _get_verification_key(settings: Settings) -> str:
    """@brief Return the JWT verification key (public RSA or HMAC secret)."""
    if settings.JWT_ALGORITHM.startswith("RS"):
        _, pub = _load_or_generate_rsa_keys(settings)
        return pub
    return settings.SECRET_KEY


# ── Password hashing ─────────────────────────────────────────────────────


def hash_password(plain: str) -> str:
    """
    @brief Hash a plaintext password using bcrypt (cost factor 12).

    @param plain The plaintext password.
    @return Bcrypt hash string.
    """
    return bcrypt.hashpw(
        plain.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    @brief Verify a plaintext password against a bcrypt hash.

    @param plain The plaintext password to check.
    @param hashed The stored bcrypt hash.
    @return True if the password matches, False otherwise.
    """
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT tokens ────────────────────────────────────────────────────────────


def create_access_token(
    subject: UUID | str,
    extra_claims: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> str:
    """
    @brief Create a short-lived JWT access token.

    @param subject User ID (UUID) to embed as the ``sub`` claim.
    @param extra_claims Optional additional claims (e.g. role, community_id).
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
    return jwt.encode(payload, _get_signing_key(s), algorithm=s.JWT_ALGORITHM)


def create_2fa_pending_token(
    subject: UUID | str,
    settings: Settings | None = None,
) -> str:
    """
    @brief Create a short-lived token for 2FA-pending login sessions.

    Valid for 5 minutes.  The user must present a TOTP code alongside
    this token to complete authentication.

    @param subject User ID.
    @param settings Override settings for testing.
    @return Encoded JWT string with type="2fa_pending".
    """
    s = settings or get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": now + timedelta(minutes=5),
        "iat": now,
        "type": "2fa_pending",
    }
    return jwt.encode(payload, _get_signing_key(s), algorithm=s.JWT_ALGORITHM)


def decode_token(
    token: str,
    expected_type: str = "access",
    settings: Settings | None = None,
) -> dict[str, Any]:
    """
    @brief Decode and validate a JWT token.

    @param token The encoded JWT string.
    @param expected_type Expected ``type`` claim.
    @param settings Override settings for testing.
    @return Decoded payload dict.
    @raises ValueError If the token is invalid, expired, or has the wrong type.
    """
    s = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            _get_verification_key(s),
            algorithms=[s.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise ValueError(_("Invalid or expired token")) from exc

    if payload.get("type") != expected_type:
        raise ValueError(_("Invalid token type"))
    if "sub" not in payload:
        raise ValueError(_("Token missing subject claim"))
    return payload


# ── Opaque refresh tokens ────────────────────────────────────────────────


def generate_refresh_token() -> str:
    """
    @brief Generate a cryptographically secure opaque refresh token.

    @return 64-character hex string.
    """
    return secrets.token_hex(32)


def hash_token(raw: str) -> str:
    """
    @brief SHA-256 hash a raw token for secure DB storage.

    @param raw The raw token string.
    @return Hex-encoded SHA-256 digest.
    """
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ── TOTP / 2FA ────────────────────────────────────────────────────────────


def generate_totp_secret() -> str:
    """
    @brief Generate a random TOTP secret (base32, 160-bit).

    @return Base32-encoded secret string.
    """
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, settings: Settings | None = None) -> str:
    """
    @brief Build an ``otpauth://`` URI for QR code generation.

    @param secret Base32 TOTP secret.
    @param email User's email address (used as account name).
    @param settings Override settings for testing.
    @return otpauth URI string.
    """
    s = settings or get_settings()
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=s.TWO_FA_ISSUER)


def verify_totp(secret: str, code: str) -> bool:
    """
    @brief Verify a TOTP code against a secret with a 1-step tolerance window.

    @param secret Base32 TOTP secret.
    @param code 6-digit TOTP code as string.
    @return True if the code is valid.
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_backup_codes(count: int = 10) -> list[str]:
    """
    @brief Generate one-time backup codes for 2FA recovery.

    @param count Number of codes to generate.
    @return List of 8-character alphanumeric codes.
    """
    alphabet = string.ascii_uppercase + string.digits
    return ["".join(secrets.choice(alphabet) for _ in range(8)) for _ in range(count)]


# ── JWKS ──────────────────────────────────────────────────────────────────


def get_jwks(settings: Settings | None = None) -> dict[str, Any]:
    """
    @brief Return the public key in JWKS (JSON Web Key Set) format.

    Used by ``/.well-known/jwks.json`` so external services can verify
    JWTs issued by this instance.

    @param settings Override settings for testing.
    @return JWKS dict with a single RSA public key entry.
    """
    s = settings or get_settings()
    if not s.JWT_ALGORITHM.startswith("RS"):
        return {"keys": []}

    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    _, pub_pem = _load_or_generate_rsa_keys(s)
    pub_key = load_pem_public_key(pub_pem.encode())
    numbers = pub_key.public_numbers()  # type: ignore[union-attr]

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": s.JWT_ALGORITHM,
                "kid": hash_token(pub_pem)[:16],
                "n": long_to_base64(numbers.n).decode(),
                "e": long_to_base64(numbers.e).decode(),
            },
        ],
    }
