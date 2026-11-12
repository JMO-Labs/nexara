"""
@file test_oidc_flow.py
@brief Tests for PKCE verifier/challenge and nonce in authorize URL.
"""

from __future__ import annotations

import hashlib
from base64 import urlsafe_b64encode
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

from app.services.oauth.flow import OAuthFlow


def _provider():
    p = MagicMock()
    p.authorization_endpoint = "https://idp.example.com/authorize"
    p.client_id = "cid"
    p.scopes = "openid profile email"
    return p


def test_verifier_is_128_chars():
    _, _, verifier = OAuthFlow().build_authorize_url(_provider(), "https://a/cb")
    assert len(verifier) == 128


def test_challenge_is_s256_of_verifier():
    url, _, verifier = OAuthFlow().build_authorize_url(_provider(), "https://a/cb")
    q = parse_qs(urlparse(url).query)
    expected = urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    assert q["code_challenge"] == [expected]
    assert q["code_challenge_method"] == ["S256"]


def test_nonce_included_and_params_encoded():
    url, state, _ = OAuthFlow().build_authorize_url(
        _provider(), "https://a/cb?x=1&y=2", nonce="n-123"
    )
    q = parse_qs(urlparse(url).query)
    assert q["nonce"] == ["n-123"]
    assert q["redirect_uri"] == ["https://a/cb?x=1&y=2"]
    assert q["scope"] == ["openid profile email"]
    assert q["state"] == [state]
