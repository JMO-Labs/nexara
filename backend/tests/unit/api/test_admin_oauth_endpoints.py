"""
@file test_admin_oauth_endpoints.py
@brief Unit tests for admin OAuth API endpoints.

All routes require admin role. Tests use mocked dependencies.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


def _admin_user():
    """@brief Mock admin user for dependency override."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = "admin"
    user.display_name = "Admin"
    return user


@pytest.fixture
def admin_override(test_app):
    """@brief Override get_current_user to return admin user."""
    from app.core.dependencies import get_current_user

    async def _override():
        return _admin_user()

    test_app.dependency_overrides[get_current_user] = _override
    yield
    test_app.dependency_overrides.pop(get_current_user, None)


class TestAdminOAuthProvidersList:
    """@brief GET /api/v1/admin/oauth/providers tests."""

    @pytest.mark.asyncio
    async def test_list_providers_returns_200(self, test_app, admin_override):
        """Admin can list OAuth providers."""
        mock_provider = MagicMock()
        mock_provider.id = uuid.uuid4()
        mock_provider.community_id = uuid.uuid4()
        mock_provider.slug = "oidc"
        mock_provider.display_name = "OIDC"
        mock_provider.icon_url = None
        mock_provider.provider_type = "oidc"
        mock_provider.issuer = None
        mock_provider.client_id = "client"
        mock_provider.scopes = "openid profile email"
        mock_provider.authorization_endpoint = None
        mock_provider.token_endpoint = None
        mock_provider.userinfo_endpoint = None
        mock_provider.jwks_uri = None
        mock_provider.end_session_endpoint = None
        mock_provider.group_mappings = {}
        mock_provider.default_role = "member"
        mock_provider.group_claim = "groups"
        mock_provider.avatar_claim = "picture"
        mock_provider.sub_claim = "sub"
        mock_provider.email_claim = "email"
        mock_provider.name_claim = "name"
        mock_provider.enabled = True
        mock_provider.auto_create_users = True
        mock_provider.seeded_from_env = False
        mock_provider.created_at = datetime.now(UTC)
        mock_provider.updated_at = mock_provider.created_at

        with patch("app.api.v1.admin_oauth.OAuthProviderRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.list = AsyncMock(return_value=([mock_provider], None))
            mock_repo_cls.return_value = mock_repo

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/admin/oauth/providers")

            assert resp.status_code == 200


class TestAdminOAuthProviderCreate:
    """@brief POST /api/v1/admin/oauth/providers tests."""

    @pytest.mark.asyncio
    async def test_create_provider_returns_201(self, test_app, admin_override):
        """Admin can create OAuth provider."""
        with (
            patch(
                "app.api.v1.admin_oauth.discover_endpoints",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch("app.api.v1.admin_oauth.OAuthProviderRepository") as mock_repo_cls,
        ):
            mock_provider = MagicMock()
            mock_provider.id = uuid.uuid4()
            mock_provider.community_id = uuid.uuid4()
            mock_provider.slug = "oidc"
            mock_provider.display_name = "OIDC"
            mock_provider.icon_url = None
            mock_provider.provider_type = "oidc"
            mock_provider.issuer = None
            mock_provider.client_id = "client"
            mock_provider.scopes = "openid profile email groups"
            mock_provider.authorization_endpoint = None
            mock_provider.token_endpoint = None
            mock_provider.userinfo_endpoint = None
            mock_provider.jwks_uri = None
            mock_provider.end_session_endpoint = None
            mock_provider.group_mappings = {}
            mock_provider.default_role = "member"
            mock_provider.group_claim = "groups"
            mock_provider.avatar_claim = "picture"
            mock_provider.sub_claim = "sub"
            mock_provider.email_claim = "email"
            mock_provider.name_claim = "name"
            mock_provider.enabled = True
            mock_provider.auto_create_users = True
            mock_provider.seeded_from_env = False
            mock_provider.created_at = datetime.now(UTC)
            mock_provider.updated_at = mock_provider.created_at

            mock_repo = AsyncMock()
            mock_repo.create = AsyncMock(return_value=mock_provider)
            mock_repo_cls.return_value = mock_repo

            with patch("app.api.v1.admin_oauth.AuditRepository") as mock_audit_cls:
                mock_audit = AsyncMock()
                mock_audit.append = AsyncMock()
                mock_audit_cls.return_value = mock_audit

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/api/v1/admin/oauth/providers",
                        json={
                            "slug": "oidc",
                            "display_name": "OIDC",
                            "provider_type": "oidc",
                            "client_id": "client",
                            "client_secret": "secret",
                        },
                    )

                assert resp.status_code == 201


class TestAdminOAuthProviderUpdate:
    """@brief PUT /api/v1/admin/oauth/providers/{id} tests."""

    @pytest.mark.asyncio
    async def test_update_provider_returns_200(self, test_app, admin_override):
        """Admin can update OAuth provider."""
        provider_id = uuid.uuid4()
        mock_provider = MagicMock()
        mock_provider.id = provider_id
        mock_provider.community_id = uuid.uuid4()
        mock_provider.slug = "oidc"
        mock_provider.display_name = "Updated OIDC"
        mock_provider.icon_url = None
        mock_provider.provider_type = "oidc"
        mock_provider.issuer = None
        mock_provider.client_id = "client"
        mock_provider.scopes = "openid profile email"
        mock_provider.authorization_endpoint = None
        mock_provider.token_endpoint = None
        mock_provider.userinfo_endpoint = None
        mock_provider.jwks_uri = None
        mock_provider.end_session_endpoint = None
        mock_provider.group_mappings = {}
        mock_provider.default_role = "member"
        mock_provider.group_claim = "groups"
        mock_provider.avatar_claim = "picture"
        mock_provider.sub_claim = "sub"
        mock_provider.email_claim = "email"
        mock_provider.name_claim = "name"
        mock_provider.enabled = True
        mock_provider.auto_create_users = True
        mock_provider.seeded_from_env = False
        mock_provider.created_at = datetime.now(UTC)
        mock_provider.updated_at = mock_provider.created_at

        with (
            patch("app.api.v1.admin_oauth.OAuthProviderRepository") as mock_repo_cls,
            patch("app.api.v1.admin_oauth.AuditRepository") as mock_audit_cls,
        ):
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_provider)
            mock_repo.update = AsyncMock(return_value=mock_provider)
            mock_repo_cls.return_value = mock_repo
            mock_audit = AsyncMock()
            mock_audit.append = AsyncMock()
            mock_audit_cls.return_value = mock_audit

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.put(
                    f"/api/v1/admin/oauth/providers/{provider_id}",
                    json={"display_name": "Updated OIDC"},
                )

            assert resp.status_code == 200


class TestAdminOAuthProviderDelete:
    """@brief DELETE /api/v1/admin/oauth/providers/{id} tests."""

    @pytest.mark.asyncio
    async def test_delete_provider_returns_200(self, test_app, admin_override):
        """Admin can delete OAuth provider."""
        provider_id = uuid.uuid4()
        mock_provider = MagicMock()
        mock_provider.id = provider_id

        with (
            patch("app.api.v1.admin_oauth.OAuthProviderRepository") as mock_repo_cls,
            patch("app.api.v1.admin_oauth.ProviderManager") as mock_mgr_cls,
            patch("app.api.v1.admin_oauth.AuditRepository") as mock_audit_cls,
        ):
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_provider)
            mock_repo.soft_delete = AsyncMock(return_value=mock_provider)
            mock_repo_cls.return_value = mock_repo
            mock_mgr = MagicMock()
            mock_mgr.invalidate_cache = MagicMock()
            mock_mgr_cls.return_value = mock_mgr
            mock_audit = AsyncMock()
            mock_audit.append = AsyncMock()
            mock_audit_cls.return_value = mock_audit

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(f"/api/v1/admin/oauth/providers/{provider_id}")

            assert resp.status_code == 200


class TestAdminOAuthProviderToggle:
    """@brief POST /api/v1/admin/oauth/providers/{id}/toggle tests."""

    @pytest.mark.asyncio
    async def test_toggle_provider_returns_200(self, test_app, admin_override):
        """Admin can toggle provider enabled state."""
        provider_id = uuid.uuid4()
        mock_provider = MagicMock()
        mock_provider.id = provider_id
        mock_provider.community_id = uuid.uuid4()
        mock_provider.slug = "oidc"
        mock_provider.display_name = "OIDC"
        mock_provider.icon_url = None
        mock_provider.provider_type = "oidc"
        mock_provider.issuer = None
        mock_provider.client_id = "client"
        mock_provider.scopes = "openid profile email"
        mock_provider.authorization_endpoint = None
        mock_provider.token_endpoint = None
        mock_provider.userinfo_endpoint = None
        mock_provider.jwks_uri = None
        mock_provider.end_session_endpoint = None
        mock_provider.group_mappings = {}
        mock_provider.default_role = "member"
        mock_provider.group_claim = "groups"
        mock_provider.avatar_claim = "picture"
        mock_provider.sub_claim = "sub"
        mock_provider.email_claim = "email"
        mock_provider.name_claim = "name"
        mock_provider.enabled = False
        mock_provider.auto_create_users = True
        mock_provider.seeded_from_env = False
        mock_provider.created_at = datetime.now(UTC)
        mock_provider.updated_at = mock_provider.created_at

        with (
            patch("app.api.v1.admin_oauth.OAuthProviderRepository") as mock_repo_cls,
            patch("app.api.v1.admin_oauth.AuditRepository") as mock_audit_cls,
        ):
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_provider)
            mock_repo.update = AsyncMock(return_value=mock_provider)
            mock_repo_cls.return_value = mock_repo
            mock_audit = AsyncMock()
            mock_audit.append = AsyncMock()
            mock_audit_cls.return_value = mock_audit

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/api/v1/admin/oauth/providers/{provider_id}/toggle")

            assert resp.status_code == 200


class TestAdminOAuthDiscover:
    """@brief POST /api/v1/admin/oauth/discover tests."""

    @pytest.mark.asyncio
    async def test_discover_returns_endpoints(self, test_app, admin_override):
        """Admin can run OIDC discovery for issuer URL."""
        with patch(
            "app.api.v1.admin_oauth.discover_endpoints",
            new_callable=AsyncMock,
            return_value={
                "authorization_endpoint": "https://auth.example.com/authorize",
                "token_endpoint": "https://auth.example.com/token",
            },
        ):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/admin/oauth/discover",
                    json={"issuer": "https://auth.example.com"},
                )

            assert resp.status_code == 200
            data = resp.json()
            assert "authorization_endpoint" in data
