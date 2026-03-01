"""
@file test_auth_service.py
@brief Unit tests for AuthService with mocked repositories.

Tests cover registration, login, refresh (including replay detection),
2FA enrollment/verification, and OIDC group mapping.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.core.security import hash_password
from app.services.auth_service import AuthService


def _make_settings() -> Settings:
    """@brief Settings fixture for auth tests (HS256 to avoid RSA key I/O)."""
    return Settings(
        SECRET_KEY="test-secret-auth-svc",
        JWT_ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=30,
        ENABLE_REGISTRATION=True,
        REQUIRE_INVITE=False,
        HIBP_CHECK_ENABLED=False,
    )


def _make_user(**overrides):
    """@brief Build a mock User object with sensible defaults."""
    user = MagicMock()
    user.id = overrides.get("id", uuid.uuid4())
    user.community_id = overrides.get(
        "community_id",
        uuid.UUID("00000000-0000-0000-0000-000000000001"),
    )
    user.email = overrides.get("email", "test@example.com")
    user.username = overrides.get("username", "testuser")
    user.display_name = overrides.get("display_name", "Test User")
    user.password_hash = overrides.get("password_hash", hash_password("valid-password1"))
    user.role = overrides.get("role", "member")
    user.is_active = overrides.get("is_active", True)
    user.totp_enabled = overrides.get("totp_enabled", False)
    user.totp_secret = overrides.get("totp_secret", None)
    user.deleted_at = None
    return user


def _make_service(session=None, settings=None):
    """@brief Construct an AuthService with a mocked DB session."""
    s = session or AsyncMock()
    svc = AuthService(s, settings or _make_settings())
    svc._user_repo = AsyncMock()
    svc._token_repo = AsyncMock()
    svc._invite_repo = AsyncMock()
    svc._settings_repo = AsyncMock()
    svc._settings_repo.get_or_create = AsyncMock(return_value=None)
    return svc


class TestRegister:
    """@brief Registration tests with mocked repos."""

    @pytest.mark.asyncio
    async def test_register_creates_user(self):
        svc = _make_service()
        svc._user_repo.email_exists.return_value = False
        svc._user_repo.username_exists.return_value = False

        created = _make_user()
        svc._user_repo.create.return_value = created

        result = await svc.register(
            email="new@example.com",
            username="newuser",
            password="strong-password123",
            display_name="New User",
        )

        assert result["access_token"]
        assert result["raw_refresh_token"]
        assert result["requires_2fa"] is False
        svc._user_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_rejects_duplicate_email(self):
        svc = _make_service()
        svc._user_repo.email_exists.return_value = True

        from app.core.exceptions import ConflictError

        with pytest.raises(ConflictError, match="already registered"):
            await svc.register(
                email="taken@example.com",
                username="newuser",
                password="strong-password123",
                display_name="Dup",
            )

    @pytest.mark.asyncio
    async def test_register_rejects_duplicate_username(self):
        svc = _make_service()
        svc._user_repo.email_exists.return_value = False
        svc._user_repo.username_exists.return_value = True

        from app.core.exceptions import ConflictError

        with pytest.raises(ConflictError, match="already taken"):
            await svc.register(
                email="new@example.com",
                username="taken",
                password="strong-password123",
                display_name="Dup",
            )

    @pytest.mark.asyncio
    async def test_register_disabled_raises(self):
        settings = _make_settings()
        settings.ENABLE_REGISTRATION = False
        svc = _make_service(settings=settings)

        from app.core.exceptions import AuthorizationError

        with pytest.raises(AuthorizationError, match="disabled"):
            await svc.register(
                email="x@x.com",
                username="x",
                password="p" * 12,
                display_name="X",
            )

    @pytest.mark.asyncio
    async def test_register_creates_profile(self):
        """@brief Register creates UserSettings (profile) alongside the user."""
        svc = _make_service()
        svc._user_repo.email_exists.return_value = False
        svc._user_repo.username_exists.return_value = False

        created = _make_user()
        svc._user_repo.create.return_value = created

        await svc.register(
            email="new@example.com",
            username="newuser",
            password="strong-password123",
            display_name="New User",
        )

        svc._settings_repo.get_or_create.assert_called_once_with(
            created.id,
            created.community_id,
        )


class TestLogin:
    """@brief Login tests with mocked repos."""

    @pytest.mark.asyncio
    async def test_login_returns_tokens(self):
        user = _make_user()
        svc = _make_service()
        svc._user_repo.find_by_email.return_value = user

        result = await svc.login(email="test@example.com", password="valid-password1")

        assert result["access_token"]
        assert result["requires_2fa"] is False

    @pytest.mark.asyncio
    async def test_login_wrong_password(self):
        user = _make_user()
        svc = _make_service()
        svc._user_repo.find_by_email.return_value = user

        from app.core.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await svc.login(email="test@example.com", password="wrong-password1")

    @pytest.mark.asyncio
    async def test_login_user_not_found(self):
        svc = _make_service()
        svc._user_repo.find_by_email.return_value = None

        from app.core.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await svc.login(email="nope@example.com", password="anything1234")

    @pytest.mark.asyncio
    async def test_login_requires_2fa(self):
        user = _make_user(totp_enabled=True, totp_secret="JBSWY3DPEHPK3PXP")
        svc = _make_service()
        svc._user_repo.find_by_email.return_value = user

        result = await svc.login(email="test@example.com", password="valid-password1")

        assert result["requires_2fa"] is True
        assert result["two_factor_token"]

    @pytest.mark.asyncio
    async def test_login_deactivated_user(self):
        user = _make_user(is_active=False)
        svc = _make_service()
        svc._user_repo.find_by_email.return_value = user

        from app.core.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError, match="deactivated"):
            await svc.login(email="test@example.com", password="valid-password1")


class TestRefresh:
    """@brief Token refresh tests including replay detection."""

    @pytest.mark.asyncio
    async def test_refresh_rotates_token(self):
        user = _make_user()
        stored = MagicMock()
        stored.id = uuid.uuid4()
        stored.user_id = user.id
        stored.family_id = uuid.uuid4()
        stored.revoked_at = None
        stored.expires_at = datetime.now(UTC) + timedelta(days=30)

        svc = _make_service()
        svc._token_repo.find_by_hash.return_value = stored
        svc._user_repo.get_by_id.return_value = user

        result = await svc.refresh("raw-refresh-token-hex")

        assert result["access_token"]
        svc._token_repo.revoke.assert_called_once_with(stored.id)

    @pytest.mark.asyncio
    async def test_refresh_replay_revokes_family(self):
        stored = MagicMock()
        stored.id = uuid.uuid4()
        stored.family_id = uuid.uuid4()
        stored.revoked_at = datetime.now(UTC)
        stored.expires_at = datetime.now(UTC) + timedelta(days=30)

        svc = _make_service()
        svc._token_repo.find_by_hash.return_value = stored

        from app.core.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError, match="reuse detected"):
            await svc.refresh("replayed-token")

        svc._token_repo.revoke_family.assert_called_once_with(stored.family_id)

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self):
        svc = _make_service()
        svc._token_repo.find_by_hash.return_value = None

        from app.core.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError, match="Invalid refresh token"):
            await svc.refresh("nonexistent-token")


class TestOIDCGroupMapping:
    """@brief OIDC group-to-role mapping tests."""

    def test_admin_group_maps_to_admin(self):
        from app.services.oidc_service import OIDCService

        svc = OIDCService.__new__(OIDCService)
        svc._settings = _make_settings()
        svc._settings.OIDC_ADMIN_GROUP = "nexara-admin"
        svc._settings.OIDC_MEMBER_GROUP = "nexara-member"

        assert svc._map_groups_to_role(["nexara-admin", "other"]) == "admin"

    def test_member_group_maps_to_member(self):
        from app.services.oidc_service import OIDCService

        svc = OIDCService.__new__(OIDCService)
        svc._settings = _make_settings()
        svc._settings.OIDC_ADMIN_GROUP = "nexara-admin"
        svc._settings.OIDC_MEMBER_GROUP = "nexara-member"

        assert svc._map_groups_to_role(["nexara-member"]) == "member"

    def test_no_matching_group_raises(self):
        from app.core.exceptions import AuthenticationError
        from app.services.oidc_service import OIDCService

        svc = OIDCService.__new__(OIDCService)
        svc._settings = _make_settings()
        svc._settings.OIDC_ADMIN_GROUP = "nexara-admin"
        svc._settings.OIDC_MEMBER_GROUP = "nexara-member"

        with pytest.raises(AuthenticationError, match="authorized group"):
            svc._map_groups_to_role(["unrelated-group"])
