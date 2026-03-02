"""
@file flow.py
@brief OAuth2 authorization code flow with PKCE.

Builds authorize URLs and exchanges authorization codes for tokens.
"""

from __future__ import annotations

from urllib.parse import urlencode

import httpx
from authlib.common.security import generate_token
from authlib.oauth2.rfc7636 import create_s256_code_challenge

from app.core.encryption import decrypt_secret, derive_fernet_key
from app.core.exceptions import AuthenticationError
from app.models.oauth_provider import OAuthProvider


class OAuthFlow:
    """
    @brief OAuth2 authorization code flow with PKCE.

    Stateless: build_authorize_url and exchange_code do not share state
    except via the returned code_verifier passed to exchange_code.
    """

    def build_authorize_url(
        self,
        provider: OAuthProvider,
        redirect_uri: str,
    ) -> tuple[str, str, str]:
        """
        @brief Build the OAuth authorization URL with PKCE.

        @param provider OAuth provider config.
        @param redirect_uri Callback URL after user authorizes.
        @return Tuple of (authorize_url, state, code_verifier).
        """
        state = generate_token(32)
        code_verifier = generate_token(64)
        code_challenge = create_s256_code_challenge(code_verifier)
        params = {
            "response_type": "code",
            "client_id": provider.client_id,
            "scope": provider.scopes or "openid profile email",
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        qs = urlencode(params)
        url = f"{provider.authorization_endpoint}?{qs}"
        return url, state, code_verifier

    async def exchange_code(
        self,
        provider: OAuthProvider,
        code: str,
        code_verifier: str,
        redirect_uri: str,
        secret_key: str,
    ) -> dict:
        """
        @brief Exchange authorization code for tokens.

        @param provider OAuth provider config.
        @param code Authorization code from IdP.
        @param code_verifier PKCE code verifier from build_authorize_url.
        @param redirect_uri Same redirect_uri used in authorize request.
        @param secret_key Application secret for decrypting client_secret.
        @return Token response dict (access_token, id_token, etc.).
        @raises AuthenticationError On non-200 response.
        """
        fernet_key = derive_fernet_key(secret_key)
        client_secret = decrypt_secret(provider.client_secret_encrypted, fernet_key)
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": provider.client_id,
            "client_secret": client_secret,
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                provider.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if resp.status_code != 200:
            raise AuthenticationError(
                message="OAuth token exchange failed",
                details={"status": resp.status_code, "body": resp.text[:200]},
            )
        return resp.json()
