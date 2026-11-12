"""
@file flow.py
@brief OAuth2 Authorization Code flow with PKCE.
"""

from __future__ import annotations

import hashlib
import secrets
from base64 import urlsafe_b64encode
from urllib.parse import urlencode
from typing import Any, cast

import httpx

from app.core.encryption import decrypt_secret, derive_fernet_key
from app.core.exceptions import AuthenticationError
from app.models.oauth_provider import OAuthProvider


class OAuthFlow:
    """
    @brief OAuth2 Authorization Code flow with PKCE.

    Builds authorize URLs and exchanges authorization codes for tokens.
    """

    def build_authorize_url(
        self,
        provider: OAuthProvider,
        redirect_uri: str,
        nonce: str | None = None,
    ) -> tuple[str, str, str]:
        """
        @brief Build the OAuth authorization URL with PKCE.

        @param provider OAuth provider configuration.
        @param redirect_uri Callback URL after authorization.
        @param nonce Optional OIDC nonce bound to the ID token.
        @return Tuple of (authorize_url, state, code_verifier).
        """
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(96)[:128]
        code_challenge = (
            urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")
        )

        auth_endpoint = provider.authorization_endpoint or ""
        params = {
            "response_type": "code",
            "client_id": provider.client_id,
            "scope": provider.scopes or "openid profile email",
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        if nonce:
            params["nonce"] = nonce
        qs = urlencode(params)
        sep = "&" if "?" in auth_endpoint else "?"
        authorize_url = f"{auth_endpoint}{sep}{qs}"

        return authorize_url, state, code_verifier

    async def exchange_code(
        self,
        provider: OAuthProvider,
        code: str,
        verifier: str,
        redirect_uri: str,
        secret_key: str | bytes,
    ) -> dict[str, Any]:
        """
        @brief Exchange authorization code for tokens.

        @param provider OAuth provider configuration.
        @param code Authorization code from callback.
        @param verifier PKCE code verifier.
        @param redirect_uri Same redirect_uri used in authorize.
        @param secret_key Fernet key (bytes) or app secret (str) to decrypt client_secret.
        @return Token response dict with access_token, id_token, etc.
        """
        if not provider.token_endpoint:
            raise AuthenticationError("no token endpoint")

        key: bytes = derive_fernet_key(secret_key) if isinstance(secret_key, str) else secret_key
        client_secret: str | None = None
        if provider.client_secret_encrypted:
            client_secret = decrypt_secret(provider.client_secret_encrypted, key)

        token_endpoint = provider.token_endpoint
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": provider.client_id,
            "code_verifier": verifier,
        }
        if client_secret:
            data["client_secret"] = client_secret

        async with httpx.AsyncClient() as client:
            resp = await client.post(token_endpoint, data=data)
            if resp.status_code != 200:
                raise AuthenticationError("token exchange failed")
            return cast(dict[str, Any], resp.json())
