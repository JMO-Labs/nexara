"""
@file auth_service.py
@brief Authentication business logic: register, login, token rotation, 2FA, password reset.

Orchestrates repositories, security utilities, and config to implement all
auth flows.  OIDC logic lives in :mod:`app.services.oidc_service` to keep
this module under the 400-line limit.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
)
from app.core.i18n import _
from app.core.security import (
    create_2fa_pending_token,
    create_access_token,
    decode_token,
    generate_backup_codes,
    generate_refresh_token,
    generate_totp_secret,
    get_totp_uri,
    hash_password,
    hash_token,
    verify_password,
    verify_totp,
)
from app.models.auth import UserBackupCode
from app.models.user import User
from app.repositories.invite_repo import InviteRepository
from app.repositories.token_repo import TokenRepository
from app.repositories.user_repo import UserRepository

logger = structlog.get_logger(__name__)


class AuthService:
    """
    @brief Stateless service encapsulating all authentication operations.

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
        self._invite_repo = InviteRepository(session)

    async def register(
        self,
        *,
        email: str,
        username: str,
        password: str,
        display_name: str,
        invite_token: str | None = None,
        community_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """
        @brief Register a new local user.

        @return Dict with ``access_token``, ``expires_in``, and ``raw_refresh_token``.
        @raises ConflictError If email or username already exists.
        @raises AuthorizationError If registration is disabled or invite is required but missing.
        """
        if not self._settings.ENABLE_REGISTRATION:
            raise AuthorizationError(message=_("Registration is currently disabled"))

        cid = community_id or uuid.UUID(self._settings.COMMUNITY_ID)
        role = "member"

        if self._settings.REQUIRE_INVITE:
            if not invite_token:
                raise AuthorizationError(message=_("An invite token is required to register"))
            invite = await self._validate_invite(invite_token)
            role = invite.role
        elif invite_token:
            invite = await self._validate_invite(invite_token)
            role = invite.role
        else:
            invite = None

        if await self._user_repo.email_exists(email):
            raise ConflictError(message=_("Email is already registered"))
        if await self._user_repo.username_exists(username):
            raise ConflictError(message=_("Username is already taken"))

        user = User(
            community_id=cid,
            email=email,
            username=username,
            display_name=display_name,
            password_hash=hash_password(password),
            role=role,
        )
        user = await self._user_repo.create(user)

        if invite:
            await self._invite_repo.mark_used(invite.id, user.id)

        logger.info("user_registered", user_id=str(user.id), email=email)
        return await self._issue_tokens(user)

    async def login(
        self,
        *,
        email: str,
        password: str,
    ) -> dict[str, Any]:
        """
        @brief Authenticate with email and password.

        @return Dict with tokens, or ``requires_2fa=True`` with a pending token.
        @raises AuthenticationError On invalid credentials.
        """
        user = await self._user_repo.find_by_email(email)
        if not user or not user.password_hash:
            raise AuthenticationError(message=_("Invalid email or password"))
        if not verify_password(password, user.password_hash):
            raise AuthenticationError(message=_("Invalid email or password"))
        if not user.is_active:
            raise AuthenticationError(message=_("Account is deactivated"))

        if user.totp_enabled:
            pending = create_2fa_pending_token(user.id, settings=self._settings)
            return {"requires_2fa": True, "two_factor_token": pending}

        await self._user_repo.update_last_seen(user.id)
        logger.info("user_logged_in", user_id=str(user.id))
        return await self._issue_tokens(user)

    async def verify_2fa_login(
        self,
        *,
        two_factor_token: str,
        code: str,
    ) -> dict[str, Any]:
        """
        @brief Complete a 2FA-pending login by verifying the TOTP code.

        @return Dict with access + refresh tokens.
        @raises AuthenticationError If the token or code is invalid.
        """
        try:
            payload = decode_token(
                two_factor_token, expected_type="2fa_pending", settings=self._settings,
            )
        except ValueError as exc:
            raise AuthenticationError(message=str(exc)) from exc

        user = await self._user_repo.get_by_id(uuid.UUID(payload["sub"]))
        if not user or not user.totp_secret:
            raise AuthenticationError(message=_("Invalid 2FA session"))

        if not verify_totp(user.totp_secret, code):
            if not await self._try_backup_code(user.id, code):
                raise AuthenticationError(message=_("Invalid 2FA code"))

        await self._user_repo.update_last_seen(user.id)
        logger.info("user_2fa_login_complete", user_id=str(user.id))
        return await self._issue_tokens(user)

    async def refresh(
        self,
        raw_refresh_token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """
        @brief Rotate a refresh token and issue a new access token.

        Detects token replay: if the presented token has already been revoked
        (i.e. the client is replaying an old token), the entire family is
        revoked as a security measure.

        @return Dict with new tokens.
        @raises AuthenticationError On invalid, expired, or replayed token.
        """
        token_hash_value = hash_token(raw_refresh_token)
        stored = await self._token_repo.find_by_hash(token_hash_value)

        if stored is None:
            raise AuthenticationError(message=_("Invalid refresh token"))

        if stored.revoked_at is not None:
            await self._token_repo.revoke_family(stored.family_id)
            logger.warning("refresh_token_replay_detected", family_id=str(stored.family_id))
            raise AuthenticationError(message=_("Token reuse detected — all sessions revoked"))

        if stored.expires_at < datetime.now(UTC):
            raise AuthenticationError(message=_("Refresh token expired"))

        await self._token_repo.revoke(stored.id)

        user = await self._user_repo.get_by_id(stored.user_id)
        if not user or not user.is_active:
            raise AuthenticationError(message=_("User not found or deactivated"))

        return await self._issue_tokens(
            user, family_id=stored.family_id,
            ip_address=ip_address, user_agent=user_agent,
        )

    async def logout(self, raw_refresh_token: str) -> None:
        """
        @brief Revoke a refresh token on logout.

        @param raw_refresh_token The raw token from the cookie/body.
        """
        token_hash_value = hash_token(raw_refresh_token)
        stored = await self._token_repo.find_by_hash(token_hash_value)
        if stored and stored.revoked_at is None:
            await self._token_repo.revoke(stored.id)
            logger.info("user_logged_out", user_id=str(stored.user_id))

    async def enroll_2fa(self, user: User) -> dict[str, str]:
        """
        @brief Start 2FA enrollment by generating a TOTP secret.

        @param user The authenticated user.
        @return Dict with ``secret`` and ``otpauth_uri``.
        """
        secret = generate_totp_secret()
        await self._user_repo.update_totp(user.id, totp_secret=secret, totp_enabled=False)
        uri = get_totp_uri(secret, user.email, settings=self._settings)
        return {"secret": secret, "otpauth_uri": uri}

    async def verify_2fa_enrollment(self, user: User, code: str) -> list[str]:
        """
        @brief Complete 2FA enrollment by verifying the first TOTP code.

        @param user The authenticated user (must have a pending totp_secret).
        @param code The 6-digit TOTP code.
        @return List of one-time backup codes.
        @raises AuthenticationError If the code is invalid.
        """
        if not user.totp_secret:
            raise AuthenticationError(message=_("2FA enrollment not started"))
        if not verify_totp(user.totp_secret, code):
            raise AuthenticationError(message=_("Invalid TOTP code"))

        await self._user_repo.update_totp(user.id, totp_enabled=True)
        codes = generate_backup_codes()
        for raw_code in codes:
            bc = UserBackupCode(user_id=user.id, code_hash=hash_token(raw_code))
            self._session.add(bc)
        await self._session.flush()

        logger.info("user_2fa_enrolled", user_id=str(user.id))
        return codes

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
        email is not found — the route handler returns the same response
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

    # ── Helpers ───────────────────────────────────────────────────────────

    async def _issue_tokens(
        self,
        user: User,
        *,
        family_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """
        @brief Create an access token + opaque refresh token pair.

        @return Dict with token data and raw_refresh_token.
        """
        access = create_access_token(
            user.id,
            extra_claims={"role": user.role, "community_id": str(user.community_id)},
            settings=self._settings,
        )
        raw_refresh = generate_refresh_token()
        fid = family_id or uuid.uuid4()
        expires = datetime.now(UTC) + timedelta(days=self._settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await self._token_repo.create(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            family_id=fid,
            expires_at=expires,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return {
            "access_token": access,
            "expires_in": self._settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "raw_refresh_token": raw_refresh,
            "requires_2fa": False,
        }

    async def _validate_invite(self, raw_token: str):  # noqa: ANN201
        """@brief Validate an invite token and return the Invite or raise."""
        invite = await self._invite_repo.find_by_token_hash(hash_token(raw_token))
        if not invite:
            raise NotFoundError(message=_("Invalid invite token"))
        if self._invite_repo.is_used(invite):
            raise ConflictError(message=_("Invite has already been used"))
        if self._invite_repo.is_expired(invite):
            from app.core.exceptions import AppError
            raise AppError(code="GONE", message=_("Invite has expired"), status_code=410)
        return invite

    async def _try_backup_code(self, user_id: uuid.UUID, code: str) -> bool:
        """@brief Attempt to consume a backup code.  Returns True on success."""
        from sqlalchemy import select

        code_hash = hash_token(code)
        stmt = select(UserBackupCode).where(
            UserBackupCode.user_id == user_id,
            UserBackupCode.code_hash == code_hash,
            UserBackupCode.used_at.is_(None),
        )
        result = await self._session.execute(stmt)
        backup = result.scalar_one_or_none()
        if not backup:
            return False
        backup.used_at = datetime.now(UTC)
        await self._session.flush()
        return True
