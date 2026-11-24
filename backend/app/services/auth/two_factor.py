"""
@file two_factor.py
@brief TOTP lifecycle: start, confirm, disable, recovery regenerate, status.

Secrets are Fernet tokens at rest; plaintext only exists transiently here.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import structlog
from cryptography.fernet import InvalidToken

from app.core.config import Settings
from app.core.encryption import decrypt_secret, derive_fernet_key, encrypt_secret
from app.core.exceptions import AppError, AuthorizationError
from app.core.i18n import _
from app.core.security import (
    generate_backup_codes,
    generate_totp_secret,
    get_totp_uri,
    verify_password,
    verify_totp,
)
from app.models.user import User
from app.repositories.two_factor_repo import TwoFactorRepository
from app.repositories.user_repo import UserRepository
from app.services.auth.totp_replay import (
    claim_totp_code,
    clear_user_attempts,
    consume_backup_code,
    normalize_totp,
    reserve_attempt,
)

logger = structlog.get_logger(__name__)

GRACE = timedelta(days=7)
"""@brief Time members get to enrol after an admin turns the policy on."""


def seal_secret(secret: str, settings: Settings) -> str:
    """@brief Encrypt a TOTP secret for storage."""
    return encrypt_secret(secret, derive_fernet_key(settings.SECRET_KEY))


def open_secret(stored: str, settings: Settings) -> str:
    """@brief Decrypt a stored TOTP secret."""
    return decrypt_secret(stored, derive_fernet_key(settings.SECRET_KEY))


def read_secret(stored: str, settings: Settings, user_id: uuid.UUID) -> str:
    """
    @brief Decrypt a stored secret, failing closed if SECRET_KEY changed.

    @raises AppError 503 ``2fa_secret_unreadable`` when the token cannot be decrypted.
    """
    try:
        return open_secret(stored, settings)
    except InvalidToken as exc:
        logger.error("2fa.secret_unreadable", user_id=str(user_id))
        raise AppError(
            code="2fa_secret_unreadable",
            message=_("Your 2FA secret can no longer be read. Ask an admin to reset your 2FA."),
            status_code=503,
        ) from exc


def _manage_key(user_id: uuid.UUID) -> uuid.UUID:
    """@brief Per-user attempt namespace for 2FA management (separate from login's)."""
    return uuid.uuid5(user_id, "2fa-manage-user")


def _bad_code() -> AppError:
    return AppError(code="invalid_code", message=_("Invalid code"), status_code=400)


class TwoFactorService:
    """@brief 2FA self-service for the signed-in user (audited, rate-limited)."""

    def __init__(
        self,
        user_repo: UserRepository,
        repo: TwoFactorRepository,
        audit: Any,
        settings: Settings,
        user: User,
        ip: str | None = None,
    ) -> None:
        self._users, self._repo, self._audit = user_repo, repo, audit
        self._settings, self._user, self._ip = settings, user, ip

    async def _log(self, action: str) -> None:
        await self._audit.append(
            actor_id=self._user.id,
            action=action,
            target_type="user",
            target_id=self._user.id,
            ip_address=self._ip,
        )

    async def _reserve(self) -> None:
        """@brief Count one management attempt; 429 when capped (own per-user counter)."""
        uid = self._user.id
        if not await reserve_attempt(f"2fa-manage:{uid}", _manage_key(uid), self._settings):
            raise AppError(
                code="too_many_attempts", message=_("Too many attempts"), status_code=429
            )

    async def _spend(self, secret: str | None, code: str, *, recovery: bool) -> bool:
        """@brief Check a TOTP (or recovery) code (caller reserved an attempt); one-time use."""
        uid = self._user.id
        canonical = normalize_totp(code)
        if canonical and secret:
            ok = verify_totp(secret, canonical) and await claim_totp_code(
                uid, canonical, self._settings
            )
        elif recovery and not canonical:
            ok = await consume_backup_code(self._repo.session, uid, code.strip())
        else:
            ok = False
        if ok:
            await clear_user_attempts(_manage_key(uid), self._settings)
        return ok

    def _active_secret(self) -> str | None:
        s = self._user.totp_secret
        if s and self._user.totp_enabled:
            return read_secret(s, self._settings, self._user.id)
        return None

    async def start(self) -> dict[str, str]:
        """
        @brief Begin enrolment: store a pending secret (not yet active).

        @return ``secret`` and ``otpauth_uri``.
        @raises AuthorizationError 2fa_already_enabled if TOTP is on.
        """
        if self._user.totp_enabled:
            raise AuthorizationError(message="2fa_already_enabled")
        secret = generate_totp_secret()
        await self._users.update_totp(
            self._user.id, totp_pending_secret=seal_secret(secret, self._settings)
        )
        uri = get_totp_uri(secret, self._user.email, settings=self._settings)
        return {"secret": secret, "otpauth_uri": uri}

    async def confirm(self, code: str) -> list[str]:
        """
        @brief Activate TOTP after the first valid code; issues fresh recovery codes.

        @raises AppError 400 on a wrong code or when enrolment was not started.
        """
        if self._user.totp_enabled:
            raise AuthorizationError(message="2fa_already_enabled")
        pending = self._user.totp_pending_secret
        if not pending:
            raise AppError(
                code="2fa_not_started", message=_("2FA enrollment not started"), status_code=400
            )
        await self._reserve()
        secret = read_secret(pending, self._settings, self._user.id)
        if not await self._spend(secret, code, recovery=False):
            raise _bad_code()
        await self._users.update_totp(
            self._user.id, totp_secret=pending, totp_pending_secret=None, totp_enabled=True
        )
        codes = generate_backup_codes()
        await self._repo.replace_recovery_codes(self._user.id, codes)
        await self._log("2fa.enabled")
        logger.info("user_2fa_enrolled", user_id=str(self._user.id))
        return codes

    async def disable(self, password: str | None, code: str | None) -> None:
        """
        @brief Turn TOTP off after proof of the password or a valid code.

        @raises AppError 400 when neither proof is valid.
        """
        ok = False
        await self._reserve()
        if password and self._user.password_hash:
            ok = verify_password(password, self._user.password_hash)
        if not ok and code:
            ok = await self._spend(self._active_secret(), code, recovery=True)
        if not ok:
            raise _bad_code()
        await self._users.update_totp(
            self._user.id, totp_secret=None, totp_pending_secret=None, totp_enabled=False
        )
        await self._repo.delete_recovery_codes(self._user.id)
        await self._log("2fa.disabled")

    async def regenerate(self, code: str) -> list[str]:
        """
        @brief Replace all recovery codes (old ones stop working).

        @raises AppError 400 on a wrong code or when TOTP is off.
        """
        await self._reserve()
        secret = self._active_secret()
        if secret is None or not await self._spend(secret, code, recovery=True):
            raise _bad_code()
        codes = generate_backup_codes()
        await self._repo.replace_recovery_codes(self._user.id, codes)
        await self._log("2fa.recovery_regenerated")
        return codes

    async def status(self) -> dict[str, Any]:
        """@brief ``totp``, ``passkeys``, ``recovery_left``, ``required``, ``grace_until``."""
        u = self._user
        passkeys = await self._repo.count_passkeys(u.id, u.community_id)
        policy = await self._repo.get_policy(u.community_id)
        applies = policy == "everyone" or (policy == "admins" and u.role == "admin")
        since: datetime | None = u.two_factor_required_since
        return {
            "totp": bool(u.totp_enabled),
            "passkeys": passkeys,
            "recovery_left": await self._repo.count_recovery_left(u.id),
            "required": applies and not u.totp_enabled and passkeys == 0,
            "grace_until": since + GRACE if applies and since else None,
        }
