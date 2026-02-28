"""
@file password_service.py
@brief Password security operations: HIBP breach checking and password reset flows.

Extracted from :mod:`app.services.auth_service` to keep each service module
under the 400-line limit.  Used by ``AuthService`` via composition.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.i18n import _
from app.core.security import hash_password, hash_token
from app.repositories.token_repo import TokenRepository
from app.repositories.user_repo import UserRepository

logger = structlog.get_logger(__name__)


class PasswordService:
    """
    @brief Service for password-related operations outside the login flow.

    Handles HaveIBeenPwned breach checks (k-anonymity range API) and the
    full password-reset lifecycle (request token, validate, apply).

    @param session Async DB session (one per request).
    @param settings App settings (injectable for tests).
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

    async def check_hibp(self, password: str) -> bool:
        """
        @brief Check a password against the HaveIBeenPwned breached-passwords API.

        Uses the k-anonymity range API: only the first 5 chars of the SHA-1
        hash are sent to the server, so the full password is never exposed.

        @param password Plaintext password to check.
        @return True if the password has been seen in a breach.
        """
        if not self._settings.HIBP_CHECK_ENABLED:
            return False

        import hashlib

        import httpx

        sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()  # noqa: S324
        prefix, suffix = sha1[:5], sha1[5:]

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://api.pwnedpasswords.com/range/{prefix}",
                    timeout=5.0,
                )
            if resp.status_code != 200:
                logger.warning("hibp_api_error", status=resp.status_code)
                return False

            for line in resp.text.splitlines():
                parts = line.split(":")
                if len(parts) == 2 and parts[0].strip() == suffix:
                    count = int(parts[1].strip())
                    logger.info("hibp_password_found", count=count)
                    return True
        except Exception:
            logger.warning("hibp_check_failed", exc_info=True)

        return False

    async def request_password_reset(self, email: str) -> str | None:
        """
        @brief Generate a password reset token if the email exists.

        Returns the raw token (caller sends the email).  Returns None if the
        email is not found -- the route handler returns the same response
        regardless to prevent account enumeration.

        @param email Email address.
        @return Raw reset token or None.
        """
        user = await self._user_repo.find_by_email(email)
        if not user:
            return None
        token = secrets.token_urlsafe(32)
        family_id = uuid.uuid4()
        expires = datetime.now(UTC) + timedelta(hours=1)
        await self._token_repo.create(
            user_id=user.id,
            token_hash=hash_token(token),
            family_id=family_id,
            expires_at=expires,
        )
        return token

    async def reset_password(self, token: str, new_password: str) -> None:
        """
        @brief Apply a new password using a valid reset token.

        @param token The raw reset token.
        @param new_password The new password.
        @raises AuthenticationError If the token is invalid or expired.
        """
        stored = await self._token_repo.find_by_hash(hash_token(token))
        if not stored or stored.revoked_at or stored.expires_at < datetime.now(UTC):
            raise AuthenticationError(message=_("Invalid or expired reset token"))

        user = await self._user_repo.get_by_id(stored.user_id)
        if not user:
            raise NotFoundError(message=_("User not found"))

        await self._user_repo.update(user, {"password_hash": hash_password(new_password)})
        await self._token_repo.revoke(stored.id)
        await self._token_repo.revoke_all_for_user(user.id)
        logger.info("password_reset_complete", user_id=str(user.id))
