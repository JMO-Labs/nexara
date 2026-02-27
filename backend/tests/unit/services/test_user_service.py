"""
@file test_user_service.py
@brief Unit tests for UserService with mocked repositories.

Tests cover profile reading, updating, password changes, email changes,
account deactivation, and Gravatar URL generation.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.core.security import hash_password
from app.services.user_service import UserService


def _make_settings() -> Settings:
    """@brief Settings fixture for user service tests."""
    return Settings(
        SECRET_KEY="test-secret-user-svc",
        JWT_ALGORITHM="HS256",
    )


def _make_user(**overrides) -> MagicMock:
    """@brief Build a mock User with sensible defaults."""
    user = MagicMock()
    user.id = overrides.get("id", uuid.uuid4())
    user.community_id = overrides.get(
        "community_id", uuid.UUID("00000000-0000-0000-0000-000000000001"),
    )
    user.email = overrides.get("email", "user@example.com")
    user.username = overrides.get("username", "testuser")
    user.display_name = overrides.get("display_name", "Test User")
    user.password_hash = overrides.get("password_hash", hash_password("current-pass1"))
    user.role = overrides.get("role", "member")
    user.is_active = overrides.get("is_active", True)
    user.avatar_url = overrides.get("avatar_url", None)
    user.bio = overrides.get("bio", None)
    user.deleted_at = None
    return user


def _make_service(session=None, settings=None) -> UserService:
    """@brief Construct a UserService with mocked repos."""
    s = session or AsyncMock()
    svc = UserService(s, settings or _make_settings())
    svc._user_repo = AsyncMock()
    svc._token_repo = AsyncMock()
    return svc


class TestGetUser:
    """@brief Fetch user by ID tests."""

    @pytest.mark.asyncio
    async def test_returns_user(self):
        user = _make_user()
        svc = _make_service()
        svc._user_repo.get_by_id.return_value = user

        result = await svc.get_user(user.id)
        assert result.id == user.id

    @pytest.mark.asyncio
    async def test_raises_not_found(self):
        svc = _make_service()
        svc._user_repo.get_by_id.return_value = None

        from app.core.exceptions import NotFoundError
        with pytest.raises(NotFoundError, match="not found"):
            await svc.get_user(uuid.uuid4())


class TestGetUserByUsername:
    """@brief Fetch user by username tests."""

    @pytest.mark.asyncio
    async def test_returns_user(self):
        user = _make_user(username="alice")
        svc = _make_service()
        svc._user_repo.find_by_username.return_value = user

        result = await svc.get_user_by_username("alice")
        assert result.username == "alice"

    @pytest.mark.asyncio
    async def test_raises_not_found(self):
        svc = _make_service()
        svc._user_repo.find_by_username.return_value = None

        from app.core.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            await svc.get_user_by_username("nonexistent")


class TestUpdateProfile:
    """@brief Profile update tests."""

    @pytest.mark.asyncio
    async def test_updates_allowed_fields(self):
        user = _make_user()
        svc = _make_service()
        updated_user = _make_user(display_name="New Name")
        svc._user_repo.update.return_value = updated_user

        result = await svc.update_profile(user, {"display_name": "New Name"})
        svc._user_repo.update.assert_called_once()
        call_args = svc._user_repo.update.call_args
        assert "display_name" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_ignores_disallowed_fields(self):
        user = _make_user()
        svc = _make_service()

        result = await svc.update_profile(user, {"role": "admin", "email": "hack@evil.com"})
        svc._user_repo.update.assert_not_called()
        assert result.id == user.id

    @pytest.mark.asyncio
    async def test_ignores_none_values(self):
        user = _make_user()
        svc = _make_service()

        result = await svc.update_profile(user, {"display_name": None})
        svc._user_repo.update.assert_not_called()


class TestChangePassword:
    """@brief Password change tests."""

    @pytest.mark.asyncio
    async def test_changes_password_and_revokes_tokens(self):
        user = _make_user()
        svc = _make_service()

        await svc.change_password(user, "current-pass1", "new-password-123")

        svc._user_repo.update.assert_called_once()
        svc._token_repo.revoke_all_for_user.assert_called_once_with(user.id)

    @pytest.mark.asyncio
    async def test_wrong_current_password_raises(self):
        user = _make_user()
        svc = _make_service()

        from app.core.exceptions import AuthenticationError
        with pytest.raises(AuthenticationError, match="incorrect"):
            await svc.change_password(user, "wrong-password1", "new-password-123")

    @pytest.mark.asyncio
    async def test_external_auth_user_raises(self):
        user = _make_user(password_hash=None)
        svc = _make_service()

        from app.core.exceptions import AuthenticationError
        with pytest.raises(AuthenticationError, match="external"):
            await svc.change_password(user, "anything1234", "new-password-123")


class TestChangeEmail:
    """@brief Email change tests."""

    @pytest.mark.asyncio
    async def test_changes_email(self):
        user = _make_user()
        svc = _make_service()
        svc._user_repo.email_exists.return_value = False
        updated = _make_user(email="new@example.com")
        svc._user_repo.update.return_value = updated

        result = await svc.change_email(user, "new@example.com", "current-pass1")
        svc._user_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_email_raises(self):
        user = _make_user()
        svc = _make_service()
        svc._user_repo.email_exists.return_value = True

        from app.core.exceptions import ConflictError
        with pytest.raises(ConflictError, match="already registered"):
            await svc.change_email(user, "taken@example.com", "current-pass1")

    @pytest.mark.asyncio
    async def test_wrong_password_raises(self):
        user = _make_user()
        svc = _make_service()

        from app.core.exceptions import AuthenticationError
        with pytest.raises(AuthenticationError, match="Invalid password"):
            await svc.change_email(user, "new@example.com", "wrong-password1")


class TestDeactivateAccount:
    """@brief Account deactivation tests."""

    @pytest.mark.asyncio
    async def test_soft_deletes_and_revokes_tokens(self):
        user = _make_user()
        svc = _make_service()

        await svc.deactivate_account(user)

        svc._user_repo.soft_delete.assert_called_once_with(user)
        svc._token_repo.revoke_all_for_user.assert_called_once_with(user.id)


class TestGetAvatarUrl:
    """@brief Avatar URL generation tests."""

    def test_returns_custom_avatar_if_set(self):
        user = _make_user(avatar_url="https://example.com/avatar.png")
        assert UserService.get_avatar_url(user) == "https://example.com/avatar.png"

    def test_returns_gravatar_fallback(self):
        user = _make_user(avatar_url=None, email="user@example.com")
        url = UserService.get_avatar_url(user)
        assert "gravatar.com/avatar" in url
        assert "d=mp" in url

    def test_gravatar_respects_size(self):
        user = _make_user(avatar_url=None)
        url = UserService.get_avatar_url(user, size=200)
        assert "s=200" in url
