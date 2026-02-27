"""
@file test_security.py
@brief Unit tests for JWT creation/validation and password hashing.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


@pytest.fixture
def test_settings() -> Settings:
    """@brief Settings for JWT tests with a known secret key."""
    return Settings(
        SECRET_KEY="test-secret-for-jwt-tests",
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=30,
        JWT_ALGORITHM="HS256",
    )


class TestPasswordHashing:
    """@brief Verify bcrypt password hashing and verification."""

    def test_hash_and_verify(self):
        hashed = hash_password("s3cret!")
        assert verify_password("s3cret!", hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)

    def test_hash_is_not_plaintext(self):
        hashed = hash_password("mypassword")
        assert hashed != "mypassword"
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
            user_id, extra_claims={"role": "admin"}, settings=test_settings
        )
        payload = decode_token(token, expected_type="access", settings=test_settings)
        assert payload["role"] == "admin"

    def test_wrong_type_raises(self, test_settings):
        token = create_access_token(uuid.uuid4(), settings=test_settings)
        with pytest.raises(ValueError, match="Invalid token type"):
            decode_token(token, expected_type="refresh", settings=test_settings)


class TestRefreshToken:
    """@brief Verify refresh token creation and decoding."""

    def test_create_and_decode(self, test_settings):
        user_id = uuid.uuid4()
        token = create_refresh_token(user_id, settings=test_settings)
        payload = decode_token(token, expected_type="refresh", settings=test_settings)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"


class TestDecodeToken:
    """@brief Verify token validation edge cases."""

    def test_invalid_token_raises(self, test_settings):
        with pytest.raises(ValueError, match="Invalid or expired"):
            decode_token("not.a.valid.token", settings=test_settings)

    def test_wrong_secret_raises(self, test_settings):
        token = create_access_token(uuid.uuid4(), settings=test_settings)
        other_settings = Settings(SECRET_KEY="different-secret")
        with pytest.raises(ValueError, match="Invalid or expired"):
            decode_token(token, settings=other_settings)
