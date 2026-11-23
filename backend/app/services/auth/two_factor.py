"""
@file two_factor.py
@brief TOTP enrollment helpers (secret generation, first-code verification, backup codes).
"""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.i18n import _
from app.core.security import (
    generate_backup_codes,
    generate_totp_secret,
    get_totp_uri,
    hash_token,
    verify_totp,
)
from app.models.auth import UserBackupCode
from app.models.user import User
from app.repositories.user_repo import UserRepository

logger = structlog.get_logger(__name__)


async def enroll(user_repo: UserRepository, settings: Settings, user: User) -> dict[str, str]:
    """
    @brief Start 2FA enrollment by generating a TOTP secret.

    @return Dict with ``secret`` and ``otpauth_uri``.
    @raises AuthorizationError If 2FA is already enabled.
    """
    if user.totp_enabled:
        raise AuthorizationError(message="2fa_already_enabled")
    secret = generate_totp_secret()
    await user_repo.update_totp(user.id, totp_secret=secret, totp_enabled=False)
    uri = get_totp_uri(secret, user.email, settings=settings)
    return {"secret": secret, "otpauth_uri": uri}


async def verify_enrollment(
    session: AsyncSession, user_repo: UserRepository, user: User, code: str
) -> list[str]:
    """
    @brief Complete enrollment by verifying the first TOTP code.

    @return List of one-time backup codes.
    @raises AuthenticationError If the code is invalid or enrollment was not started.
    """
    if not user.totp_secret:
        raise AuthenticationError(message=_("2FA enrollment not started"))
    if not verify_totp(user.totp_secret, code):
        raise AuthenticationError(message=_("Invalid TOTP code"))

    await user_repo.update_totp(user.id, totp_enabled=True)
    codes = generate_backup_codes()
    for raw_code in codes:
        session.add(UserBackupCode(user_id=user.id, code_hash=hash_token(raw_code)))
    await session.flush()

    logger.info("user_2fa_enrolled", user_id=str(user.id))
    return codes
