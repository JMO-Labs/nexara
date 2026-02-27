"""
@file test_schemas_user.py
@brief Unit tests for user Pydantic schemas: validation rules, field constraints.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.user import (
    EmailChangeRequest,
    PasswordChangeRequest,
    UserDetailResponse,
    UserResponse,
    UserUpdateRequest,
)


class TestUserResponse:
    """@brief Public user profile response tests."""

    def test_minimal(self):
        now = datetime.now(UTC)
        resp = UserResponse(
            id=uuid4(),
            username="alice",
            display_name="Alice",
            role="member",
            created_at=now,
        )
        assert resp.avatar_url is None
        assert resp.last_seen_at is None

    def test_full(self):
        now = datetime.now(UTC)
        resp = UserResponse(
            id=uuid4(),
            username="bob",
            display_name="Bob",
            avatar_url="https://example.com/avatar.png",
            bio="Hello!",
            pronouns="he/him",
            location="NYC",
            website_url="https://bob.dev",
            role="admin",
            created_at=now,
            last_seen_at=now,
        )
        assert resp.role == "admin"
        assert resp.bio == "Hello!"


class TestUserDetailResponse:
    """@brief Detailed user profile response tests (private fields)."""

    def test_includes_private_fields(self):
        now = datetime.now(UTC)
        resp = UserDetailResponse(
            id=uuid4(),
            username="alice",
            display_name="Alice",
            email="alice@example.com",
            email_verified=True,
            role="member",
            totp_enabled=False,
            storage_used=1024,
            storage_quota=1073741824,
            created_at=now,
            updated_at=now,
        )
        assert resp.email == "alice@example.com"
        assert resp.totp_enabled is False
        assert resp.storage_used == 1024


class TestUserUpdateRequest:
    """@brief Profile update request validation."""

    def test_all_none_valid(self):
        req = UserUpdateRequest()
        assert req.display_name is None
        assert req.bio is None

    def test_display_name_min_length(self):
        with pytest.raises(ValidationError):
            UserUpdateRequest(display_name="")

    def test_display_name_max_length(self):
        with pytest.raises(ValidationError):
            UserUpdateRequest(display_name="A" * 101)

    def test_bio_max_length(self):
        with pytest.raises(ValidationError):
            UserUpdateRequest(bio="A" * 501)

    def test_valid_update(self):
        req = UserUpdateRequest(
            display_name="New Name",
            bio="A short bio",
            location="Berlin",
            birthday=date(1990, 1, 1),
        )
        assert req.display_name == "New Name"
        assert req.birthday == date(1990, 1, 1)


class TestPasswordChangeRequest:
    """@brief Password change request validation."""

    def test_valid(self):
        req = PasswordChangeRequest(
            current_password="old-password",
            new_password="new-password-12",
        )
        assert req.new_password == "new-password-12"

    def test_new_password_min_length(self):
        with pytest.raises(ValidationError):
            PasswordChangeRequest(
                current_password="old",
                new_password="short",
            )

    def test_current_password_required(self):
        with pytest.raises(ValidationError):
            PasswordChangeRequest(
                current_password="",
                new_password="a" * 12,
            )


class TestEmailChangeRequest:
    """@brief Email change request validation."""

    def test_valid(self):
        req = EmailChangeRequest(
            new_email="new@example.com",
            password="current-pass",
        )
        assert req.new_email == "new@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            EmailChangeRequest(
                new_email="not-an-email",
                password="pass",
            )

    def test_password_required(self):
        with pytest.raises(ValidationError):
            EmailChangeRequest(
                new_email="new@example.com",
                password="",
            )
