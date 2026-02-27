"""
@file oidc_service.py
@brief OIDC/OAuth2 login flow with PKCE, token exchange, and user provisioning.

Handles the authorization code flow with a single OIDC provider.  Multi-provider
support is deferred to a future phase.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from base64 import urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError
from app.core.i18n import _
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_token,
)
from app.models.user import User
from app.repositories.token_repo import TokenRepository
from app.repositories.user_repo import UserRepository

logger = structlog.get_logger(__name__)


class OIDCService:
    """
    @brief Service for OIDC authorization-code + PKCE flow.

    State and code-verifier are stored in Valkey (keyed by state nonce)
    so the callback can validate the round-trip.

    @param session Async DB session.
    @param settings App settings.
    """

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._user_repo = UserRepository(session)
        self._token_repo = TokenRepository(session)

    def build_authorize_url(self) -> tuple[str, str, str]:
        """
        @brief Build the OIDC authorization redirect URL with PKCE.

        @return Tuple of (authorize_url, state, code_verifier).
        @raises AuthenticationError If OIDC is not configured.
        """
        s = self._settings
        if not s.OIDC_ISSUER or not s.OIDC_CLIENT_ID:
            raise AuthenticationError(message=_("OIDC is not configured"))

        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest(),
        ).decode().rstrip("=")

        params = {
            "response_type": "code",
            "client_id": s.OIDC_CLIENT_ID,
            "scope": s.OIDC_SCOPES,
            "redirect_uri": self._callback_uri(),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        authorize_url = f"{s.OIDC_ISSUER}/authorize?{qs}"

        return authorize_url, state, code_verifier

    async def handle_callback(
        self,
        code: str,
        code_verifier: str,
    ) -> dict[str, Any]:
        """
        @brief Exchange the authorization code for tokens and provision the user.

        @param code Authorization code from the IdP.
        @param code_verifier PKCE code verifier from the initial request.
        @return Dict with access_token, expires_in, raw_refresh_token.
        @raises AuthenticationError If token exchange fails or groups are insufficient.
        """
        s = self._settings
        token_data = await self._exchange_code(code, code_verifier)
        id_token_claims = await self._verify_id_token(token_data.get("id_token", ""))

        oidc_sub = id_token_claims.get("sub")
        if not oidc_sub:
            raise AuthenticationError(message=_("OIDC response missing subject"))

        email = id_token_claims.get("email", "")
        name = id_token_claims.get("name", id_token_claims.get("preferred_username", ""))
        groups = id_token_claims.get("groups", [])

        role = self._map_groups_to_role(groups)

        user = await self._user_repo.find_by_oidc_sub(oidc_sub)
        if not user:
            user = await self._user_repo.find_by_email(email)
            if user:
                await self._user_repo.update(user, {"oidc_sub": oidc_sub, "role": role})
            else:
                username = self._derive_username(email, name)
                user = User(
                    community_id=uuid.UUID(s.COMMUNITY_ID),
                    email=email,
                    username=username,
                    display_name=name or username,
                    oidc_sub=oidc_sub,
                    role=role,
                    email_verified=True,
                )
                user = await self._user_repo.create(user)
                logger.info("oidc_user_created", user_id=str(user.id), email=email)
        else:
            await self._user_repo.update(user, {"role": role})

        await self._user_repo.update_last_seen(user.id)
        return await self._issue_tokens(user)

    def _map_groups_to_role(self, groups: list[str]) -> str:
        """
        @brief Map OIDC group claims to an application role.

        @param groups List of group names from the id_token.
        @return Role string (admin, member, or viewer).
        @raises AuthenticationError If no valid group mapping exists.
        """
        s = self._settings
        if s.OIDC_ADMIN_GROUP in groups:
            return "admin"
        if s.OIDC_MEMBER_GROUP in groups:
            return "member"
        raise AuthenticationError(
            message=_("Your account does not belong to an authorized group"),
        )

    async def _exchange_code(self, code: str, code_verifier: str) -> dict[str, Any]:
        """@brief Exchange authorization code for tokens at the IdP token endpoint."""
        s = self._settings
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{s.OIDC_ISSUER}/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self._callback_uri(),
                    "client_id": s.OIDC_CLIENT_ID,
                    "client_secret": s.OIDC_CLIENT_SECRET,
                    "code_verifier": code_verifier,
                },
            )
        if resp.status_code != 200:
            logger.error("oidc_token_exchange_failed", status=resp.status_code, body=resp.text)
            raise AuthenticationError(message=_("OIDC token exchange failed"))
        return resp.json()

    async def _verify_id_token(self, id_token: str) -> dict[str, Any]:
        """
        @brief Decode and validate the OIDC id_token.

        A production-grade implementation should fetch the provider's JWKS
        and verify the signature.  For Phase 1, we trust the token endpoint
        response (TLS-protected) and decode without signature verification,
        relying on the confidential client + PKCE for security.
        """
        from jose import jwt as jose_jwt

        try:
            claims = jose_jwt.get_unverified_claims(id_token)
        except Exception as exc:
            raise AuthenticationError(message=_("Invalid OIDC id_token")) from exc
        return claims

    def _callback_uri(self) -> str:
        """@brief Build the OIDC callback URI."""
        return f"{self._settings.ALLOWED_ORIGINS.split(',')[0].strip()}/api/v1/auth/oidc/callback"

    @staticmethod
    def _derive_username(email: str, name: str) -> str:
        """@brief Derive a URL-safe username from email or name."""
        import re

        base = name or email.split("@")[0]
        clean = re.sub(r"[^a-zA-Z0-9_-]", "", base.replace(" ", "_"))
        return clean[:30] or f"user_{secrets.token_hex(4)}"

    async def _issue_tokens(self, user: User) -> dict[str, Any]:
        """@brief Create access + refresh token pair for an OIDC-authenticated user."""
        s = self._settings
        access = create_access_token(
            user.id,
            extra_claims={"role": user.role, "community_id": str(user.community_id)},
            settings=s,
        )
        raw_refresh = generate_refresh_token()
        family_id = uuid.uuid4()
        expires = datetime.now(UTC) + timedelta(days=s.REFRESH_TOKEN_EXPIRE_DAYS)
        await self._token_repo.create(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            family_id=family_id,
            expires_at=expires,
        )
        return {
            "access_token": access,
            "expires_in": s.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "raw_refresh_token": raw_refresh,
            "requires_2fa": False,
        }
