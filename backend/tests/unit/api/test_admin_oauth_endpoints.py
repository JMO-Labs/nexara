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
        mock_provider.preset = None
        mock_provider.allowed_domains = []
        mock_provider.required_group = None
        mock_provider.username_claim = "preferred_username"
        mock_provider.sync_profile = True
        mock_provider.enabled = True
        mock_provider.auto_create_users = True
        mock_provider.seeded_from_env = False
        mock_provider.discovery_url = None
        mock_provider.claim_mapping = {}
        mock_provider.created_at = datetime.now(UTC)
        mock_provider.updated_at = mock_provider.created_at

        with patch(
            "app.services.oauth.admin_oauth_service.OAuthProviderRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.list = AsyncMock(return_value=([mock_provider], None))
            mock_repo_cls.return_value = mock_repo

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/admin/oauth/providers")

            assert resp.status_code == 200
            assert resp.json()[0]["callback_url"] == (
                "http://localhost:3000/api/v1/oauth/oidc/callback"
            )


class TestAdminOAuthProviderCreate:
    """@brief POST /api/v1/admin/oauth/providers tests."""

    @pytest.mark.asyncio
    async def test_create_provider_returns_201(self, test_app, admin_override):
        """Admin can create OAuth provider."""
        with (
            patch(
                "app.services.oauth.admin_oauth_service.discover_endpoints",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.oauth.admin_oauth_service.OAuthProviderRepository"
            ) as mock_repo_cls,
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
            mock_provider.preset = None
            mock_provider.allowed_domains = []
            mock_provider.required_group = None
            mock_provider.username_claim = "preferred_username"
            mock_provider.sync_profile = True
            mock_provider.enabled = True
            mock_provider.auto_create_users = True
            mock_provider.seeded_from_env = False
            mock_provider.discovery_url = None
            mock_provider.claim_mapping = {}
            mock_provider.created_at = datetime.now(UTC)
            mock_provider.updated_at = mock_provider.created_at

            mock_repo = AsyncMock()
            mock_repo.create = AsyncMock(return_value=mock_provider)
            mock_repo_cls.return_value = mock_repo

            with patch("app.services.oauth.admin_oauth_service.AuditRepository") as mock_audit_cls:
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
        mock_provider.preset = None
        mock_provider.allowed_domains = []
        mock_provider.required_group = None
        mock_provider.username_claim = "preferred_username"
        mock_provider.sync_profile = True
        mock_provider.enabled = True
        mock_provider.auto_create_users = True
        mock_provider.seeded_from_env = False
        mock_provider.discovery_url = None
        mock_provider.claim_mapping = {}
        mock_provider.created_at = datetime.now(UTC)
        mock_provider.updated_at = mock_provider.created_at

        with (
            patch(
                "app.services.oauth.admin_oauth_service.OAuthProviderRepository"
            ) as mock_repo_cls,
            patch("app.services.oauth.admin_oauth_service.AuditRepository") as mock_audit_cls,
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
            patch(
                "app.services.oauth.admin_oauth_service.OAuthProviderRepository"
            ) as mock_repo_cls,
            patch("app.services.oauth.admin_oauth_service.ProviderManager") as mock_mgr_cls,
            patch("app.services.oauth.admin_oauth_service.AuditRepository") as mock_audit_cls,
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
        mock_provider.preset = None
        mock_provider.allowed_domains = []
        mock_provider.required_group = None
        mock_provider.username_claim = "preferred_username"
        mock_provider.sync_profile = True
        mock_provider.enabled = False
        mock_provider.auto_create_users = True
        mock_provider.seeded_from_env = False
        mock_provider.discovery_url = None
        mock_provider.claim_mapping = {}
        mock_provider.created_at = datetime.now(UTC)
        mock_provider.updated_at = mock_provider.created_at

        with (
            patch(
                "app.services.oauth.admin_oauth_service.OAuthProviderRepository"
            ) as mock_repo_cls,
            patch("app.services.oauth.admin_oauth_service.AuditRepository") as mock_audit_cls,
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
            "app.api.v1.admin_oauth_tools.discover_endpoints",
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


class TestAdminOAuthGroupMappingPreview:
    """@brief GET /api/v1/admin/oauth/providers/{id}/group-mapping-preview tests."""

    @pytest.mark.asyncio
    async def test_preview_returns_entries(self, test_app, admin_override):
        """Preview resolves the provider mapping for sample groups."""
        provider = MagicMock()
        provider.claim_mapping = {"group_mapping": {}}
        entries = [
            {
                "group": "eng",
                "subgroup_id": None,
                "role": "admin",
                "subgroup_exists": None,
                "matched": True,
            }
        ]
        with (
            patch("app.services.oauth.admin_oauth_service.OAuthProviderRepository") as repo_cls,
            patch(
                "app.services.oauth.admin_oauth_service.preview_group_mapping",
                new_callable=AsyncMock,
                return_value=entries,
            ) as preview,
        ):
            repo_cls.return_value.get_by_id = AsyncMock(return_value=provider)
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    f"/api/v1/admin/oauth/providers/{uuid.uuid4()}/group-mapping-preview",
                    params={"groups": ["eng"]},
                )

        assert resp.status_code == 200
        assert resp.json() == {"entries": entries}
        assert preview.await_args.args[3] == ["eng"]

    @pytest.mark.asyncio
    async def test_preview_unknown_provider_returns_404(self, test_app, admin_override):
        """Preview for a missing provider yields the not-found envelope."""
        with patch("app.services.oauth.admin_oauth_service.OAuthProviderRepository") as repo_cls:
            repo_cls.return_value.get_by_id = AsyncMock(return_value=None)
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    f"/api/v1/admin/oauth/providers/{uuid.uuid4()}/group-mapping-preview"
                )

        assert resp.status_code == 404


class TestAdminOAuthPresets:
    """@brief GET /api/v1/admin/oauth/presets tests."""

    @pytest.mark.asyncio
    async def test_lists_nine_presets(self, test_app, admin_override):
        """Admin sees all nine built-in presets."""
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/oauth/presets")

        assert resp.status_code == 200
        assert len(resp.json()) == 9
        assert {p["key"] for p in resp.json()} >= {"authentik", "github", "custom"}

    @pytest.mark.asyncio
    async def test_member_forbidden(self, test_app):
        """Non-admin gets 403."""
        from app.core.dependencies import get_current_user

        member = MagicMock(id=uuid.uuid4(), role="member")
        test_app.dependency_overrides[get_current_user] = lambda: member
        try:
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/admin/oauth/presets")
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 403


class TestProviderInputValidation:
    """@brief Schema validation for preset and allowed_domains."""

    BASE = {
        "slug": "x",
        "display_name": "X",
        "provider_type": "oidc",
        "client_id": "c",
        "client_secret": "s",
    }

    def test_unknown_preset_rejected(self):
        from pydantic import ValidationError

        from app.schemas.oauth import OAuthProviderCreate, OAuthProviderUpdate

        with pytest.raises(ValidationError):
            OAuthProviderCreate(**self.BASE, preset="nope")
        with pytest.raises(ValidationError):
            OAuthProviderUpdate(preset="nope")
        assert OAuthProviderCreate(**self.BASE, preset="github").preset == "github"

    def test_domains_normalised(self):
        from app.schemas.oauth import OAuthProviderCreate, OAuthProviderUpdate

        raw = [" @Example.COM ", "example.com", "", "  ", "b.org"]
        assert OAuthProviderCreate(**self.BASE, allowed_domains=raw).allowed_domains == [
            "example.com",
            "b.org",
        ]
        assert OAuthProviderUpdate(allowed_domains=raw).allowed_domains == ["example.com", "b.org"]

    @pytest.mark.asyncio
    async def test_unknown_preset_422_via_api(self, test_app, admin_override):
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
            resp = await c.post("/api/v1/admin/oauth/providers", json={**self.BASE, "preset": "x"})
        assert resp.status_code == 422


class TestCallbackTemplate:
    """@brief GET /api/v1/admin/oauth/callback-url."""

    @pytest.mark.asyncio
    async def test_returns_template_with_slug_placeholder(self, test_app, admin_override):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/oauth/callback-url")
        assert resp.status_code == 200
        assert resp.json() == {"template": "http://localhost:3000/api/v1/oauth/{slug}/callback"}

    @pytest.mark.asyncio
    async def test_requires_auth(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/oauth/callback-url")
        assert resp.status_code in (401, 403)
