"""
@file test_oauth_coverage_services.py
@brief Cover remaining branches in claim_mapper, discovery and token_verifier.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from authlib.jose import JsonWebKey, JsonWebToken

from app.services.oauth import discovery, token_verifier
from app.services.oauth.claim_mapper import map_claims


def test_map_claims_groups_not_list_or_string_yields_empty():
    """Non-list, non-string groups claim (e.g. int) maps to no groups."""
    result = map_claims({"sub": "u1", "groups": 5}, None)
    assert result.groups == []


async def test_fetch_discovery_missing_endpoints_raises():
    """Discovery doc lacking token_endpoint is rejected."""
    discovery.clear_cache()
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "issuer": "https://idp.example.com",
        "authorization_endpoint": "https://idp.example.com/auth",
    }
    client = AsyncMock()
    client.get.return_value = resp
    client.__aenter__.return_value = client
    with (
        patch.object(discovery, "_validate_https_public"),
        patch.object(discovery.httpx, "AsyncClient", return_value=client),
        pytest.raises(ValueError, match="missing authorization/token endpoint"),
    ):
        await discovery.fetch_discovery("https://idp.example.com/.well-known/x", 5)
    discovery.clear_cache()


async def test_verify_id_token_sets_issuer_option_and_accepts_valid_token():
    """Provider with an issuer enforces iss; a matching token verifies."""
    key = JsonWebKey.generate_key("RSA", 2048, is_private=True)
    jwks = {"keys": [key.as_dict(is_private=False)]}
    token = JsonWebToken(["RS256"]).encode(
        {"alg": "RS256", "kid": key.as_dict()["kid"]},
        {"iss": "https://idp.example.com", "sub": "u1", "exp": 4102444800, "nonce": "n1"},
        key,
    )
    provider = SimpleNamespace(
        jwks_uri="https://idp.example.com/jwks", issuer="https://idp.example.com"
    )
    with patch.object(token_verifier, "_fetch_jwks", AsyncMock(return_value=jwks)):
        claims = await token_verifier.verify_id_token(token.decode(), provider, nonce="n1")
    assert claims["sub"] == "u1"
