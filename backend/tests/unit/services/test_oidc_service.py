"""
@file test_oidc_service.py
@brief Unit tests for OIDCService: authorization URL, callback, user provisioning.

Uses mocked HTTP clients and repositories to test the OIDC flow
without requiring a live identity provider.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.services.oidc_service import OIDCService


def _make_settings(**overrides) -> Settings:
    """@brief OIDC-configured settings for tests."""
    defaults = {
        "SECRET_KEY": "test-secret-oidc",
        "JWT_ALGORITHM": "HS256",
        "OIDC_ISSUER": "https://idp.example.com",
        "OIDC_CLIENT_ID": "nexara-client",
        "OIDC_CLIENT_SECRET": "client-secret",
        "OIDC_ADMIN_GROUP": "nexara-admin",
        "OIDC_MEMBER_GROUP": "nexara-member",
        "OIDC_SCOPES": "openid profile email groups",
        "ALLOWED_ORIGINS": "https://app.example.com",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _make_service(session=None, settings=None) -> OIDCService:
    """@brief Construct an OIDCService with mocked repos."""
    s = session or AsyncMock()
    svc = OIDCService(s, settings or _make_settings())
    svc._user_repo = AsyncMock()
    svc._token_repo = AsyncMock()
    return svc


class TestBuildAuthorizeUrl:
    """@brief Authorization URL generation tests."""

    def test_returns_url_with_pkce(self):
        svc = _make_service()
        url, state, code_verifier = svc.build_authorize_url()

        assert "https://idp.example.com/authorize" in url
        assert "client_id=nexara-client" in url
        assert "code_challenge_method=S256" in url
        assert "code_challenge=" in url
        assert state
        assert code_verifier

    def test_state_is_unique(self):
        svc = _make_service()
        _, state1, _ = svc.build_authorize_url()
        _, state2, _ = svc.build_authorize_url()
        assert state1 != state2

    def test_raises_when_oidc_not_configured(self):
        settings = _make_settings(OIDC_ISSUER="", OIDC_CLIENT_ID="")
        svc = _make_service(settings=settings)

        from app.core.exceptions import AuthenticationError
        with pytest.raises(AuthenticationError, match="not configured"):
            svc.build_authorize_url()


class TestMapGroupsToRole:
    """@brief OIDC group-to-role mapping tests."""

    def test_admin_group_maps_to_admin(self):
        svc = _make_service()
        assert svc._map_groups_to_role(["nexara-admin", "other"]) == "admin"

    def test_member_group_maps_to_member(self):
        svc = _make_service()
        assert svc._map_groups_to_role(["nexara-member"]) == "member"

    def test_admin_takes_precedence_over_member(self):
        svc = _make_service()
        assert svc._map_groups_to_role(["nexara-admin", "nexara-member"]) == "admin"

    def test_no_matching_group_raises(self):
        svc = _make_service()
        from app.core.exceptions import AuthenticationError
        with pytest.raises(AuthenticationError, match="authorized group"):
            svc._map_groups_to_role(["unrelated-group"])


class TestDeriveUsername:
    """@brief Username derivation from OIDC claims."""

    def test_from_name(self):
        result = OIDCService._derive_username("user@example.com", "John Doe")
        assert result == "John_Doe"

    def test_from_email_when_name_empty(self):
        result = OIDCService._derive_username("alice@example.com", "")
        assert result == "alice"

    def test_strips_special_chars(self):
        result = OIDCService._derive_username("user@example.com", "José García!")
        assert "!" not in result
        assert "é" not in result

    def test_truncates_long_names(self):
        result = OIDCService._derive_username("user@example.com", "A" * 50)
        assert len(result) <= 30

    def test_fallback_when_cleaned_is_empty(self):
        result = OIDCService._derive_username("@example.com", "!!!")
        assert result.startswith("user_")


class TestCallbackUri:
    """@brief Callback URI construction tests."""

    def test_uses_first_allowed_origin(self):
        svc = _make_service()
        uri = svc._callback_uri()
        assert uri == "https://app.example.com/api/v1/auth/oidc/callback"


class TestHandleCallback:
    """@brief Full OIDC callback flow tests with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_creates_new_user(self):
        svc = _make_service()
        svc._user_repo.find_by_oidc_sub.return_value = None
        svc._user_repo.find_by_email.return_value = None

        created_user = MagicMock()
        created_user.id = uuid.uuid4()
        created_user.community_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        created_user.role = "member"
        svc._user_repo.create.return_value = created_user

        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {
            "id_token": "dummy.token.here",
            "access_token": "at",
        }

        claims = {
            "sub": "oidc-sub-123",
            "email": "new@example.com",
            "name": "New User",
            "groups": ["nexara-member"],
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = mock_token_resp

        with (
            patch(
                "app.services.oidc_service.httpx.AsyncClient",
                return_value=mock_client,
            ),
            patch(
                "app.services.oidc_service.OIDCService._verify_id_token",
                return_value=claims,
            ),
        ):
            result = await svc.handle_callback("auth-code", "code-verifier")

        assert result["access_token"]
        assert result["raw_refresh_token"]
        svc._user_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_links_existing_user_by_email(self):
        existing_user = MagicMock()
        existing_user.id = uuid.uuid4()
        existing_user.community_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        existing_user.role = "member"

        svc = _make_service()
        svc._user_repo.find_by_oidc_sub.return_value = None
        svc._user_repo.find_by_email.return_value = existing_user

        claims = {
            "sub": "oidc-sub-456",
            "email": "existing@example.com",
            "groups": ["nexara-member"],
        }

        with (
            patch("app.services.oidc_service.httpx.AsyncClient"),
            patch(
                "app.services.oidc_service.OIDCService._verify_id_token",
                return_value=claims,
            ),
            patch(
                "app.services.oidc_service.OIDCService._exchange_code",
                return_value={"id_token": "t"},
            ),
        ):
            await svc.handle_callback("auth-code", "code-verifier")

        svc._user_repo.update.assert_any_call(
            existing_user, {"oidc_sub": "oidc-sub-456", "role": "member"},
        )

    @pytest.mark.asyncio
    async def test_missing_sub_raises(self):
        svc = _make_service()
        claims = {"email": "test@example.com"}

        with (
            patch(
                "app.services.oidc_service.OIDCService._exchange_code",
                return_value={"id_token": "t"},
            ),
            patch(
                "app.services.oidc_service.OIDCService._verify_id_token",
                return_value=claims,
            ),
        ):
            from app.core.exceptions import AuthenticationError
            with pytest.raises(AuthenticationError, match="missing subject"):
                await svc.handle_callback("code", "verifier")
