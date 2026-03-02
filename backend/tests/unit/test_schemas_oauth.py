"""
@file test_schemas_oauth.py
@brief Unit tests for OAuth Pydantic schemas.

Tests schema validation for OAuthProviderCreate, OAuthProviderUpdate,
OAuthProviderResponse, OAuthProviderListItem, OAuthExchangeRequest,
and updated AuthConfigResponse.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.auth import AuthConfigResponse, OAuthProviderListItem
from app.schemas.oauth import (
    OAuthExchangeRequest,
    OAuthProviderCreate,
    OAuthProviderResponse,
    OAuthProviderUpdate,
)


class TestOAuthProviderCreate:
    """@brief OAuthProviderCreate validation tests."""

    def test_required_fields(self):
        """OAuthProviderCreate requires slug, display_name, provider_type, client_id, secret."""
        req = OAuthProviderCreate(
            slug="oidc",
            display_name="OIDC",
            provider_type="oidc",
            client_id="my-client",
            client_secret="secret",
        )
        assert req.slug == "oidc"
        assert req.display_name == "OIDC"
        assert req.provider_type == "oidc"
        assert req.client_id == "my-client"
        assert req.client_secret == "secret"

    def test_optional_fields_default(self):
        """OAuthProviderCreate accepts optional fields with defaults."""
        req = OAuthProviderCreate(
            slug="google",
            display_name="Google",
            provider_type="oauth2",
            client_id="g-client",
            client_secret="g-secret",
        )
        assert req.issuer is None
        assert req.icon_url is None
        assert req.scopes is None

    def test_missing_required_rejected(self):
        """OAuthProviderCreate rejects missing required fields."""
        with pytest.raises(ValidationError):
            OAuthProviderCreate(
                slug="oidc",
                display_name="OIDC",
                provider_type="oidc",
                client_id="my-client",
                # client_secret missing
            )


class TestOAuthProviderUpdate:
    """@brief OAuthProviderUpdate validation tests."""

    def test_all_fields_optional(self):
        """OAuthProviderUpdate accepts empty body."""
        req = OAuthProviderUpdate()
        assert req.slug is None
        assert req.display_name is None

    def test_partial_update(self):
        """OAuthProviderUpdate accepts partial fields."""
        req = OAuthProviderUpdate(display_name="New Name", enabled=False)
        assert req.display_name == "New Name"
        assert req.enabled is False


class TestOAuthProviderResponse:
    """@brief OAuthProviderResponse serialization tests."""

    def test_from_model_excludes_client_secret(self):
        """OAuthProviderResponse must NOT include client_secret_encrypted."""
        model = type(
            "OAuthProvider",
            (),
            {
                "id": uuid4(),
                "community_id": uuid4(),
                "slug": "oidc",
                "display_name": "OIDC",
                "icon_url": "https://example.com/icon.png",
                "provider_type": "oidc",
                "issuer": "https://auth.example.com",
                "client_id": "client",
                "client_secret_encrypted": "encrypted-secret-should-not-appear",
                "scopes": "openid profile email",
                "authorization_endpoint": "https://auth.example.com/authorize",
                "token_endpoint": "https://auth.example.com/token",
                "userinfo_endpoint": "https://auth.example.com/userinfo",
                "jwks_uri": "https://auth.example.com/jwks",
                "end_session_endpoint": None,
                "group_mappings": {},
                "default_role": "member",
                "group_claim": "groups",
                "avatar_claim": "picture",
                "sub_claim": "sub",
                "email_claim": "email",
                "name_claim": "name",
                "enabled": True,
                "auto_create_users": True,
                "seeded_from_env": False,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )()
        resp = OAuthProviderResponse.model_validate(model)
        assert resp.slug == "oidc"
        assert resp.display_name == "OIDC"
        assert (
            not hasattr(resp, "client_secret_encrypted")
            or getattr(resp, "client_secret_encrypted", None) is None
        )
        # Ensure the schema excludes it - check model_fields
        assert "client_secret_encrypted" not in OAuthProviderResponse.model_fields


class TestOAuthProviderListItem:
    """@brief OAuthProviderListItem validation tests."""

    def test_required_fields(self):
        """OAuthProviderListItem has slug, display_name, optional icon_url."""
        item = OAuthProviderListItem(
            slug="oidc",
            display_name="OIDC",
            icon_url=None,
        )
        assert item.slug == "oidc"
        assert item.display_name == "OIDC"
        assert item.icon_url is None

    def test_with_icon_url(self):
        """OAuthProviderListItem accepts icon_url."""
        item = OAuthProviderListItem(
            slug="google",
            display_name="Google",
            icon_url="https://example.com/google.svg",
        )
        assert item.icon_url == "https://example.com/google.svg"


class TestOAuthExchangeRequest:
    """@brief OAuthExchangeRequest validation tests."""

    def test_code_required(self):
        """OAuthExchangeRequest requires code field."""
        req = OAuthExchangeRequest(code="exchange-code-123")
        assert req.code == "exchange-code-123"

    def test_missing_code_rejected(self):
        """OAuthExchangeRequest rejects missing code."""
        with pytest.raises(ValidationError):
            OAuthExchangeRequest()


class TestAuthConfigResponse:
    """@brief AuthConfigResponse with oauth_providers tests."""

    def test_oidc_enabled_backward_compat(self):
        """AuthConfigResponse has oidc_enabled for backward compat."""
        resp = AuthConfigResponse(
            oidc_enabled=True,
            registration_enabled=True,
            oauth_providers=[OAuthProviderListItem(slug="oidc", display_name="OIDC")],
        )
        assert resp.oidc_enabled is True
        assert resp.registration_enabled is True
        assert len(resp.oauth_providers) == 1
        assert resp.oauth_providers[0].slug == "oidc"

    def test_local_auth_enabled(self):
        """AuthConfigResponse has local_auth_enabled."""
        resp = AuthConfigResponse(
            oidc_enabled=False,
            registration_enabled=True,
            local_auth_enabled=True,
            oauth_providers=[],
        )
        assert resp.local_auth_enabled is True

    def test_empty_oauth_providers_default(self):
        """AuthConfigResponse defaults oauth_providers to empty list."""
        resp = AuthConfigResponse(
            oidc_enabled=False,
            registration_enabled=True,
        )
        assert resp.oauth_providers == []
