"""
@file test_token_verifier.py
@brief Tests for ID token verification and claim extraction.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthenticationError
from app.models.oauth_provider import OAuthProvider
from app.services.oauth.token_verifier import extract_claims, verify_id_token
from app.services.oauth.user_provisioner import OAuthAuthResult


def _make_provider(
    sub_claim: str = "sub",
    email_claim: str = "email",
    name_claim: str = "name",
    group_claim: str = "groups",
    avatar_claim: str = "picture",
    jwks_uri: str | None = "https://idp.example.com/jwks",
) -> OAuthProvider:
    """@brief Create a mock OAuthProvider with claim mappings."""
    p = MagicMock(spec=OAuthProvider)
    p.sub_claim = sub_claim
    p.email_claim = email_claim
    p.name_claim = name_claim
    p.group_claim = group_claim
    p.avatar_claim = avatar_claim
    p.jwks_uri = jwks_uri
    return p


class TestVerifyIdToken:
    """@brief verify_id_token with mocked JWKS."""

    @pytest.mark.asyncio
    async def test_verifies_and_returns_claims(self):
        """@brief With mocked JWKS, verifies and returns claims."""
        provider = _make_provider()
        id_token = "header.payload.signature"
        expected_claims = {"sub": "user-123", "email": "u@ex.com", "name": "User"}

        class MockClaims(dict):
            def validate(self):
                pass

        mock_claims = MockClaims(expected_claims)
        with (
            patch(
                "app.services.oauth.token_verifier._fetch_jwks",
                new_callable=AsyncMock,
                return_value={"keys": []},
            ),
            patch(
                "app.services.oauth.token_verifier.JsonWebToken",
            ) as mock_jwt_cls,
        ):
            mock_jwt = MagicMock()
            mock_jwt.decode.return_value = mock_claims
            mock_jwt_cls.return_value = mock_jwt

            result = await verify_id_token(id_token, provider)

        assert result["sub"] == "user-123"
        assert result["email"] == "u@ex.com"

    @pytest.mark.asyncio
    async def test_invalid_token_raises_authentication_error(self):
        """@brief Invalid token raises AuthenticationError."""
        provider = _make_provider()

        with (
            patch(
                "app.services.oauth.token_verifier._fetch_jwks",
                new_callable=AsyncMock,
                return_value={"keys": []},
            ),
            patch(
                "app.services.oauth.token_verifier.JsonWebToken",
            ) as mock_jwt_cls,
        ):
            mock_jwt = MagicMock()
            mock_jwt.decode.side_effect = Exception("Invalid signature")
            mock_jwt_cls.return_value = mock_jwt

            with pytest.raises(AuthenticationError, match="Invalid|id_token|token"):
                await verify_id_token("invalid.token.here", provider)


class TestExtractClaims:
    """@brief extract_claims maps provider claim names to OAuthAuthResult."""

    def test_extracts_sub_email_name_groups_avatar(self):
        """@brief Extracts sub, email, name, groups, avatar using provider mapping."""
        provider = _make_provider()
        claims = {
            "sub": "oidc-sub-456",
            "email": "alice@example.com",
            "name": "Alice",
            "groups": ["admins", "users"],
            "picture": "https://idp.example.com/avatar.png",
        }

        result = extract_claims(claims, provider)

        assert isinstance(result, OAuthAuthResult)
        assert result.sub == "oidc-sub-456"
        assert result.email == "alice@example.com"
        assert result.display_name == "Alice"
        assert result.groups == ["admins", "users"]
        assert result.avatar_url == "https://idp.example.com/avatar.png"

    def test_custom_claim_names(self):
        """@brief Uses provider's custom claim names."""
        provider = _make_provider(
            sub_claim="user_id",
            email_claim="mail",
            name_claim="displayName",
            group_claim="roles",
            avatar_claim="photo",
        )
        claims = {
            "user_id": "custom-sub",
            "mail": "bob@example.com",
            "displayName": "Bob",
            "roles": ["member"],
            "photo": "https://idp.example.com/bob.jpg",
        }

        result = extract_claims(claims, provider)

        assert result.sub == "custom-sub"
        assert result.email == "bob@example.com"
        assert result.display_name == "Bob"
        assert result.groups == ["member"]
        assert result.avatar_url == "https://idp.example.com/bob.jpg"
