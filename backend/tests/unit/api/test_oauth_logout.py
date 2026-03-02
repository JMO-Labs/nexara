"""
@file test_oauth_logout.py
@brief Unit tests for RP-initiated logout (end_session_url in logout response).

Verifies that logout returns end_session_url when the user has an OAuth link
to a provider with end_session_endpoint; otherwise returns normal response.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_optional_user
from app.core.security import create_access_token


def _make_token(user_id: uuid.UUID) -> str:
    """@brief Create a valid access token for the given user."""
    from app.core.config import Settings

    settings = Settings(
        SECRET_KEY="test-unit-secret",
        JWT_ALGORITHM="HS256",
        WAF_ENABLED=False,
        ENABLE_METRICS=False,
    )
    return create_access_token(user_id, settings=settings)


class TestOAuthLogout:
    """@brief POST /api/v1/auth/logout with OAuth RP-initiated logout."""

    @pytest.mark.asyncio
    async def test_logout_user_without_oauth_link_returns_no_end_session_url(self, test_app):
        """Logout for user without OAuth link returns normal response (no end_session_url)."""
        user_id = uuid.uuid4()
        token = _make_token(user_id)
        mock_user = MagicMock()
        mock_user.id = user_id

        async def _override_user():
            return mock_user

        test_app.dependency_overrides[get_optional_user] = _override_user
        try:
            with (
                patch("app.api.v1.auth.AuthService") as mock_svc_cls,
                patch("app.repositories.oauth_repo.UserOAuthLinkRepository") as mock_link_repo_cls,
            ):
                mock_svc = AsyncMock()
                mock_svc_cls.return_value = mock_svc

                mock_link_repo = AsyncMock()
                mock_link_repo.find_links_for_user = AsyncMock(return_value=[])
                mock_link_repo_cls.return_value = mock_link_repo

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/api/v1/auth/logout",
                        headers={"Authorization": f"Bearer {token}"},
                    )

            assert resp.status_code == 200
            data = resp.json()
            assert "message" in data
            assert data.get("end_session_url") is None
        finally:
            del test_app.dependency_overrides[get_optional_user]

    @pytest.mark.asyncio
    async def test_logout_user_with_oauth_link_and_end_session_returns_url(self, test_app):
        """Logout for user with OAuth link to provider with end_session_endpoint."""
        user_id = uuid.uuid4()
        provider_id = uuid.uuid4()
        token = _make_token(user_id)
        mock_user = MagicMock()
        mock_user.id = user_id

        mock_link = MagicMock()
        mock_link.provider_id = provider_id

        mock_provider = MagicMock()
        mock_provider.end_session_endpoint = "https://idp.example/session/end"

        async def _override_user():
            return mock_user

        test_app.dependency_overrides[get_optional_user] = _override_user
        try:
            with (
                patch("app.api.v1.auth.AuthService") as mock_svc_cls,
                patch("app.repositories.oauth_repo.UserOAuthLinkRepository") as mock_link_repo_cls,
                patch(
                    "app.repositories.oauth_repo.OAuthProviderRepository"
                ) as mock_provider_repo_cls,
            ):
                mock_svc = AsyncMock()
                mock_svc_cls.return_value = mock_svc

                mock_link_repo = AsyncMock()
                mock_link_repo.find_links_for_user = AsyncMock(return_value=[mock_link])
                mock_link_repo_cls.return_value = mock_link_repo

                mock_provider_repo = AsyncMock()
                mock_provider_repo.get_by_id = AsyncMock(return_value=mock_provider)
                mock_provider_repo_cls.return_value = mock_provider_repo

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/api/v1/auth/logout",
                        headers={"Authorization": f"Bearer {token}"},
                    )

            assert resp.status_code == 200
            data = resp.json()
            assert data.get("end_session_url") == "https://idp.example/session/end"
        finally:
            del test_app.dependency_overrides[get_optional_user]

    @pytest.mark.asyncio
    async def test_logout_user_with_oauth_link_no_end_session_endpoint(self, test_app):
        """Logout for user with OAuth link but provider has no end_session_endpoint."""
        user_id = uuid.uuid4()
        provider_id = uuid.uuid4()
        token = _make_token(user_id)
        mock_user = MagicMock()
        mock_user.id = user_id

        mock_link = MagicMock()
        mock_link.provider_id = provider_id

        mock_provider = MagicMock()
        mock_provider.end_session_endpoint = None

        async def _override_user():
            return mock_user

        test_app.dependency_overrides[get_optional_user] = _override_user
        try:
            with (
                patch("app.api.v1.auth.AuthService") as mock_svc_cls,
                patch("app.repositories.oauth_repo.UserOAuthLinkRepository") as mock_link_repo_cls,
                patch(
                    "app.repositories.oauth_repo.OAuthProviderRepository"
                ) as mock_provider_repo_cls,
            ):
                mock_svc = AsyncMock()
                mock_svc_cls.return_value = mock_svc

                mock_link_repo = AsyncMock()
                mock_link_repo.find_links_for_user = AsyncMock(return_value=[mock_link])
                mock_link_repo_cls.return_value = mock_link_repo

                mock_provider_repo = AsyncMock()
                mock_provider_repo.get_by_id = AsyncMock(return_value=mock_provider)
                mock_provider_repo_cls.return_value = mock_provider_repo

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/api/v1/auth/logout",
                        headers={"Authorization": f"Bearer {token}"},
                    )

            assert resp.status_code == 200
            data = resp.json()
            assert data.get("end_session_url") is None
        finally:
            del test_app.dependency_overrides[get_optional_user]
