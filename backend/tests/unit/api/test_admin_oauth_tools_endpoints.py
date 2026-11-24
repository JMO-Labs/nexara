"""
@file test_admin_oauth_tools_endpoints.py
@brief Admin OAuth tool endpoints: discovery, mapping preview, presets, input validation.

Split from test_admin_oauth_endpoints.py (CRUD) to keep files under 400 lines.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient


def _admin_user():
    """@brief Mock admin user for dependency override."""
    return MagicMock(id=uuid.uuid4(), role="admin", display_name="Admin")


@pytest.fixture
def admin_override(test_app):
    """@brief Override get_current_user to return an admin."""
    from app.core.dependencies import get_current_user

    test_app.dependency_overrides[get_current_user] = _admin_user
    yield
    test_app.dependency_overrides.pop(get_current_user, None)


class TestAdminOAuthDiscover:
    """@brief POST /api/v1/admin/oauth/discover tests."""

    @pytest.mark.asyncio
    async def test_discover_returns_endpoints(self, test_app, admin_override):
        """Admin can run OIDC discovery for issuer URL."""
        with patch(
            "app.services.oauth.admin_oauth_service.discover_endpoints",
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


class TestDiscoveryAndRoleErrors:
    """@brief invalid discovery -> 422 envelope; default_role restricted."""

    @pytest.mark.asyncio
    async def test_discover_failure_is_422_invalid_discovery(self, test_app, admin_override):
        with patch(
            "app.services.oauth.admin_oauth_service.discover_endpoints",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("down"),
        ):
            async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
                resp = await c.post("/api/v1/admin/oauth/discover", json={"issuer": "https://x"})
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "invalid_discovery"

    def test_default_role_restricted(self):
        from pydantic import ValidationError

        from app.schemas.oauth import OAuthProviderCreate, OAuthProviderUpdate

        base = TestProviderInputValidation.BASE
        with pytest.raises(ValidationError):
            OAuthProviderCreate(**base, default_role="Admin")
        with pytest.raises(ValidationError):
            OAuthProviderUpdate(default_role="owner")
        assert OAuthProviderCreate(**base, default_role="viewer").default_role == "viewer"
