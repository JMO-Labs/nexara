"""
@file test_schemas_auth.py
@brief Unit tests for auth Pydantic schemas: validation rules, field constraints.

Ensures all request/response models enforce their documented constraints.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    InviteCreateRequest,
    InviteResponse,
    LoginRequest,
    LoginResponse,
    OIDCCallbackParams,
    PasswordResetConfirmPayload,
    PasswordResetRequestPayload,
    RefreshResponse,
    RegisterRequest,
    TokenResponse,
    TwoFactorEnrollResponse,
    TwoFactorLoginRequest,
    TwoFactorVerifyRequest,
    TwoFactorVerifyResponse,
)


class TestLoginRequest:
    """@brief Login request validation."""

    def test_valid(self):
        req = LoginRequest(email="user@example.com", password="pass")
        assert req.email == "user@example.com"

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="not-an-email", password="pass")

    def test_empty_password_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com", password="")


class TestRegisterRequest:
    """@brief Registration request validation."""

    def test_valid(self):
        req = RegisterRequest(
            email="new@example.com",
            username="user_name-1",
            password="a" * 12,
            display_name="Display",
        )
        assert req.username == "user_name-1"

    def test_short_password_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="a@b.com", username="user1", password="short", display_name="D",
            )

    def test_short_username_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="a@b.com", username="ab", password="a" * 12, display_name="D",
            )

    def test_long_username_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="a@b.com", username="a" * 31, password="a" * 12, display_name="D",
            )

    def test_username_special_chars_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="a@b.com", username="user@name", password="a" * 12, display_name="D",
            )

    def test_invite_token_optional(self):
        req = RegisterRequest(
            email="a@b.com", username="user1", password="a" * 12, display_name="D",
        )
        assert req.invite_token is None


class TestTokenResponse:
    """@brief Token response serialization."""

    def test_defaults(self):
        resp = TokenResponse(access_token="jwt", expires_in=900)
        assert resp.token_type == "bearer"

    def test_expires_in_required(self):
        with pytest.raises(ValidationError):
            TokenResponse(access_token="jwt")


class TestLoginResponse:
    """@brief Login response with optional 2FA fields."""

    def test_normal_login(self):
        resp = LoginResponse(access_token="jwt", expires_in=900)
        assert resp.requires_2fa is False
        assert resp.two_factor_token is None

    def test_2fa_pending(self):
        resp = LoginResponse(requires_2fa=True, two_factor_token="pending-jwt")
        assert resp.access_token is None


class TestRefreshResponse:
    """@brief Refresh response validation."""

    def test_valid(self):
        resp = RefreshResponse(access_token="jwt", expires_in=900)
        assert resp.token_type == "bearer"


class TestTwoFactorSchemas:
    """@brief 2FA enrollment and verification schemas."""

    def test_enroll_response(self):
        resp = TwoFactorEnrollResponse(secret="BASE32SECRET", otpauth_uri="otpauth://...")
        assert resp.secret == "BASE32SECRET"

    def test_verify_request_valid(self):
        req = TwoFactorVerifyRequest(code="123456")
        assert len(req.code) == 6

    def test_verify_request_too_short(self):
        with pytest.raises(ValidationError):
            TwoFactorVerifyRequest(code="12345")

    def test_verify_request_too_long(self):
        with pytest.raises(ValidationError):
            TwoFactorVerifyRequest(code="123456789")

    def test_login_request(self):
        req = TwoFactorLoginRequest(two_factor_token="jwt", code="123456")
        assert req.two_factor_token == "jwt"

    def test_verify_response(self):
        resp = TwoFactorVerifyResponse(backup_codes=["code1", "code2"])
        assert len(resp.backup_codes) == 2


class TestPasswordResetSchemas:
    """@brief Password reset request/confirm schemas."""

    def test_request_valid(self):
        req = PasswordResetRequestPayload(email="user@example.com")
        assert req.email

    def test_request_invalid_email(self):
        with pytest.raises(ValidationError):
            PasswordResetRequestPayload(email="not-email")

    def test_confirm_valid(self):
        req = PasswordResetConfirmPayload(token="abc", new_password="a" * 12)
        assert req.token == "abc"

    def test_confirm_short_password(self):
        with pytest.raises(ValidationError):
            PasswordResetConfirmPayload(token="abc", new_password="short")


class TestOIDCCallbackParams:
    """@brief OIDC callback query parameters."""

    def test_valid(self):
        params = OIDCCallbackParams(code="auth-code", state="state-nonce")
        assert params.code == "auth-code"


class TestInviteSchemas:
    """@brief Invite creation and response schemas."""

    def test_create_defaults(self):
        req = InviteCreateRequest(email="invite@example.com")
        assert req.role == "member"

    def test_create_admin_role(self):
        req = InviteCreateRequest(email="admin@example.com", role="admin")
        assert req.role == "admin"

    def test_create_invalid_role(self):
        with pytest.raises(ValidationError):
            InviteCreateRequest(email="a@b.com", role="superuser")

    def test_response_from_attributes(self):
        now = datetime.now(UTC)
        resp = InviteResponse(
            id=uuid4(),
            email="a@b.com",
            role="member",
            created_by=uuid4(),
            expires_at=now,
            created_at=now,
        )
        assert resp.used_at is None
