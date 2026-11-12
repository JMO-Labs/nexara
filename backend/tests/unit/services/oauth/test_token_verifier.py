"""
@file test_token_verifier.py
@brief Unit tests for OAuth ID token verification and claim extraction.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.oauth.token_verifier as tv
from app.core.exceptions import AuthenticationError
from app.services.oauth.token_verifier import extract_claims, verify_id_token
from app.services.oauth.user_provisioner import OAuthAuthResult


@pytest.fixture(autouse=True)
def clear_jwks_cache():
    """Clear module-level JWKS cache between tests."""
    tv._JWKS_CACHE.clear()
    yield
    tv._JWKS_CACHE.clear()


def _make_provider(
    sub_claim="sub",
    email_claim="email",
    name_claim="name",
    group_claim="groups",
    avatar_claim="picture",
    jwks_uri="https://idp.example.com/jwks.json",
):
    """Create a mock provider with claim name attributes."""
    provider = MagicMock()
    provider.sub_claim = sub_claim
    provider.email_claim = email_claim
    provider.name_claim = name_claim
    provider.group_claim = group_claim
    provider.avatar_claim = avatar_claim
    provider.jwks_uri = jwks_uri
    return provider


class TestExtractClaims:
    """@brief Tests for extract_claims function."""

    def test_extracts_standard_claims(self):
        """extract_claims extracts standard claims (sub, email, name, groups, avatar)."""
        provider = _make_provider()
        claims = {
            "sub": "user-123",
            "email": "user@example.com",
            "name": "Test User",
            "groups": ["admins", "members"],
            "picture": "https://example.com/avatar.png",
        }
        result = extract_claims(claims, provider)
        assert isinstance(result, OAuthAuthResult)
        assert result.sub == "user-123"
        assert result.email == "user@example.com"
        assert result.display_name == "Test User"
        assert result.groups == ["admins", "members"]
        assert result.avatar_url == "https://example.com/avatar.png"

    def test_uses_custom_claim_names_from_provider(self):
        """extract_claims uses custom claim names from provider config."""
        provider = _make_provider(
            sub_claim="oidc_sub",
            email_claim="mail",
            name_claim="display_name",
            group_claim="roles",
            avatar_claim="avatar",
        )
        claims = {
            "oidc_sub": "sub-456",
            "mail": "custom@example.com",
            "display_name": "Custom Name",
            "roles": ["admin"],
            "avatar": "https://example.com/avatar.jpg",
        }
        result = extract_claims(claims, provider)
        assert result.sub == "sub-456"
        assert result.email == "custom@example.com"
        assert result.display_name == "Custom Name"
        assert result.groups == ["admin"]
        assert result.avatar_url == "https://example.com/avatar.jpg"

    def test_handles_missing_optional_claims(self):
        """extract_claims handles missing optional claims."""
        provider = _make_provider()
        claims = {"sub": "user-789"}
        result = extract_claims(claims, provider)
        assert result.sub == "user-789"
        assert result.email is None
        assert result.display_name is None
        assert result.groups == []
        assert result.avatar_url is None

    def test_handles_groups_as_single_string(self):
        """extract_claims handles groups as single string (not list)."""
        provider = _make_provider()
        claims = {"sub": "user-1", "groups": "single-group"}
        result = extract_claims(claims, provider)
        assert result.groups == ["single-group"]


class _MockClaims(dict):
    """Dict-like claims with validate method for authlib compatibility."""

    def validate(self):
        pass


class TestVerifyIdToken:
    """@brief Tests for verify_id_token async function."""

    @pytest.mark.asyncio
    async def test_with_jwks_uri_fetches_and_verifies(self):
        """verify_id_token with jwks_uri fetches and verifies (mock httpx + authlib)."""
        provider = _make_provider(jwks_uri="https://idp.example.com/jwks.json")
        mock_jwks = {"keys": []}
        mock_decoded = _MockClaims({"sub": "user-1", "email": "user@example.com"})

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_jwks
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_jwt = MagicMock()
        mock_jwt.decode.return_value = mock_decoded

        with patch("app.services.oauth.token_verifier.httpx.AsyncClient", return_value=mock_client):
            with patch(
                "app.services.oauth.token_verifier.JsonWebKey.import_key_set",
                return_value=MagicMock(),
            ):
                with patch(
                    "app.services.oauth.token_verifier.JsonWebToken",
                    return_value=mock_jwt,
                ):
                    result = await verify_id_token("fake.jwt.token", provider)

        assert result["sub"] == "user-1"
        assert result["email"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_without_jwks_uri_is_rejected(self):
        """verify_id_token never accepts unsigned tokens (no jwks_uri)."""
        provider = _make_provider(jwks_uri=None)
        with pytest.raises(AuthenticationError):
            await verify_id_token("header.payload.sig", provider)


class TestFetchJwks:
    """@brief Tests for _fetch_jwks caching."""

    @pytest.mark.asyncio
    async def test_uses_cache_on_second_call(self):
        """_fetch_jwks uses cache on second call."""
        from app.services.oauth.token_verifier import _fetch_jwks

        mock_jwks = {"keys": [{"kid": "1"}]}
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_jwks
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.oauth.token_verifier.httpx.AsyncClient", return_value=mock_client):
            result1 = await _fetch_jwks("https://idp.example.com/jwks")
            result2 = await _fetch_jwks("https://idp.example.com/jwks")

        assert result1 == result2 == mock_jwks
        mock_client.get.assert_called_once()


def _signed(claims, key=None):
    from authlib.jose import JsonWebKey, jwt

    key = key or JsonWebKey.generate_key("RSA", 2048, is_private=True, options={"kid": "k1"})
    tok = jwt.encode({"alg": "RS256", "kid": "k1"}, claims, key).decode()
    return tok, {"keys": [key.as_dict(is_private=False)]}


class TestStrictVerification:
    """@brief Signature, expiry, nonce and issuer enforcement."""

    @pytest.fixture(autouse=True)
    def _clear(self):
        tv._JWKS_CACHE.clear()

    def _run(self, tok, jwks, provider, **kw):
        import time as _t  # noqa: F401

        async def go():
            with patch.object(tv, "_fetch_jwks", AsyncMock(return_value=jwks)):
                return await verify_id_token(tok, provider, **kw)

        return go()

    @pytest.mark.asyncio
    async def test_valid_token_with_nonce(self):
        import time

        provider = _make_provider(jwks_uri="https://idp/jwks")
        tok, jwks = _signed({"sub": "u", "nonce": "n1", "exp": int(time.time()) + 300})
        out = await self._run(tok, jwks, provider, nonce="n1")
        assert out["sub"] == "u"

    @pytest.mark.asyncio
    async def test_expired_rejected(self):
        import time

        provider = _make_provider(jwks_uri="https://idp/jwks")
        tok, jwks = _signed({"sub": "u", "nonce": "n1", "exp": int(time.time()) - 300})
        with pytest.raises(AuthenticationError):
            await self._run(tok, jwks, provider, nonce="n1")

    @pytest.mark.asyncio
    async def test_missing_exp_rejected(self):
        provider = _make_provider(jwks_uri="https://idp/jwks")
        tok, jwks = _signed({"sub": "u", "nonce": "n1"})
        with pytest.raises(AuthenticationError):
            await self._run(tok, jwks, provider, nonce="n1")

    @pytest.mark.asyncio
    async def test_nonce_mismatch_rejected(self):
        import time

        provider = _make_provider(jwks_uri="https://idp/jwks")
        tok, jwks = _signed({"sub": "u", "nonce": "bad", "exp": int(time.time()) + 300})
        with pytest.raises(AuthenticationError):
            await self._run(tok, jwks, provider, nonce="n1")

    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self):
        import time

        from authlib.jose import JsonWebKey

        provider = _make_provider(jwks_uri="https://idp/jwks")
        tok, _ = _signed({"sub": "u", "exp": int(time.time()) + 300})
        other = JsonWebKey.generate_key("RSA", 2048, is_private=True, options={"kid": "k1"})
        with pytest.raises(AuthenticationError):
            await self._run(tok, {"keys": [other.as_dict(is_private=False)]}, provider)

    @pytest.mark.asyncio
    async def test_no_jwks_uri_rejected_when_strict(self):
        provider = _make_provider(jwks_uri=None)
        with pytest.raises(AuthenticationError):
            await verify_id_token("a.b.c", provider, nonce="n1")
