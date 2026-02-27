"""
@file test_security.py
@brief Unit tests for JWT creation/validation, password hashing, TOTP, and token utilities.
"""

import os
import uuid
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.security import (
    create_2fa_pending_token,
    create_access_token,
    decode_token,
    generate_backup_codes,
    generate_refresh_token,
    generate_totp_secret,
    get_jwks,
    hash_password,
    hash_token,
    verify_password,
    verify_totp,
)


@pytest.fixture
def test_settings() -> Settings:
    """@brief Settings for JWT tests using HS256 (simpler for unit tests)."""
    return Settings(
        SECRET_KEY="test-secret-for-jwt-tests",
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=30,
        JWT_ALGORITHM="HS256",
    )


@pytest.fixture
def rs256_settings(tmp_path: Path) -> Settings:
    """@brief Settings for RS256 JWT tests with auto-generated keys."""
    return Settings(
        JWT_ALGORITHM="RS256",
        JWT_PRIVATE_KEY_PATH=str(tmp_path / "jwt_private.pem"),
        JWT_PUBLIC_KEY_PATH=str(tmp_path / "jwt_public.pem"),
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=30,
    )


class TestPasswordHashing:
    """@brief Verify bcrypt password hashing and verification."""

    def test_hash_and_verify(self):
        hashed = hash_password("s3cret-password!")
        assert verify_password("s3cret-password!", hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct-password")
        assert not verify_password("wrong-password", hashed)

    def test_hash_is_not_plaintext(self):
        hashed = hash_password("mypassword1234")
        assert hashed != "mypassword1234"
        assert hashed.startswith("$2b$")


class TestAccessToken:
    """@brief Verify access token creation and decoding."""

    def test_create_and_decode(self, test_settings):
        user_id = uuid.uuid4()
        token = create_access_token(user_id, settings=test_settings)
        payload = decode_token(token, expected_type="access", settings=test_settings)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_extra_claims_included(self, test_settings):
        user_id = uuid.uuid4()
        token = create_access_token(
            user_id, extra_claims={"role": "admin"}, settings=test_settings,
        )
        payload = decode_token(token, expected_type="access", settings=test_settings)
        assert payload["role"] == "admin"

    def test_wrong_type_raises(self, test_settings):
        token = create_access_token(uuid.uuid4(), settings=test_settings)
        with pytest.raises(ValueError, match="Invalid token type"):
            decode_token(token, expected_type="refresh", settings=test_settings)

    def test_rs256_create_and_decode(self, rs256_settings):
        """@brief Verify RS256 key auto-generation, signing, and verification."""
        import app.core.security as sec

        sec._private_key = None
        sec._public_key = None

        user_id = uuid.uuid4()
        token = create_access_token(
            user_id, extra_claims={"role": "member"}, settings=rs256_settings,
        )
        payload = decode_token(token, expected_type="access", settings=rs256_settings)
        assert payload["sub"] == str(user_id)
        assert payload["role"] == "member"
        assert Path(rs256_settings.JWT_PRIVATE_KEY_PATH).exists()

        sec._private_key = None
        sec._public_key = None


class TestTwoFactorPendingToken:
    """@brief Verify 2FA pending tokens for partial login."""

    def test_create_and_decode(self, test_settings):
        user_id = uuid.uuid4()
        token = create_2fa_pending_token(user_id, settings=test_settings)
        payload = decode_token(token, expected_type="2fa_pending", settings=test_settings)
        assert payload["sub"] == str(user_id)

    def test_access_type_mismatch(self, test_settings):
        token = create_2fa_pending_token(uuid.uuid4(), settings=test_settings)
        with pytest.raises(ValueError, match="Invalid token type"):
            decode_token(token, expected_type="access", settings=test_settings)


class TestDecodeToken:
    """@brief Verify token validation edge cases."""

    def test_invalid_token_raises(self, test_settings):
        with pytest.raises(ValueError, match="Invalid or expired"):
            decode_token("not.a.valid.token", settings=test_settings)

    def test_wrong_secret_raises(self, test_settings):
        token = create_access_token(uuid.uuid4(), settings=test_settings)
        other_settings = Settings(SECRET_KEY="different-secret", JWT_ALGORITHM="HS256")
        with pytest.raises(ValueError, match="Invalid or expired"):
            decode_token(token, settings=other_settings)


class TestRefreshToken:
    """@brief Verify opaque refresh token generation and hashing."""

    def test_generate_is_64_hex_chars(self):
        raw = generate_refresh_token()
        assert len(raw) == 64
        int(raw, 16)  # must be valid hex

    def test_uniqueness(self):
        tokens = {generate_refresh_token() for _ in range(100)}
        assert len(tokens) == 100


class TestHashToken:
    """@brief Verify SHA-256 token hashing."""

    def test_consistent_hash(self):
        assert hash_token("test") == hash_token("test")

    def test_different_input_different_hash(self):
        assert hash_token("a") != hash_token("b")

    def test_hash_length(self):
        assert len(hash_token("x")) == 64


class TestTOTP:
    """@brief Verify TOTP secret generation and code verification."""

    def test_generate_secret(self):
        secret = generate_totp_secret()
        assert len(secret) == 32

    def test_verify_valid_code(self):
        import pyotp

        secret = generate_totp_secret()
        code = pyotp.TOTP(secret).now()
        assert verify_totp(secret, code) is True

    def test_verify_invalid_code(self):
        secret = generate_totp_secret()
        assert verify_totp(secret, "000000") is False


class TestBackupCodes:
    """@brief Verify backup code generation."""

    def test_count(self):
        codes = generate_backup_codes(count=10)
        assert len(codes) == 10

    def test_length(self):
        codes = generate_backup_codes()
        assert all(len(c) == 8 for c in codes)

    def test_uniqueness(self):
        codes = generate_backup_codes()
        assert len(set(codes)) == len(codes)


class TestJWKS:
    """@brief Verify JWKS output for RS256 keys."""

    def test_jwks_rs256(self, rs256_settings):
        import app.core.security as sec

        sec._private_key = None
        sec._public_key = None

        jwks = get_jwks(rs256_settings)
        assert len(jwks["keys"]) == 1
        key = jwks["keys"][0]
        assert key["kty"] == "RSA"
        assert key["use"] == "sig"
        assert key["alg"] == "RS256"
        assert "n" in key
        assert "e" in key

        sec._private_key = None
        sec._public_key = None

    def test_jwks_hs256_returns_empty(self, test_settings):
        jwks = get_jwks(test_settings)
        assert jwks["keys"] == []
