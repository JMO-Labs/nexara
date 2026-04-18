"""
@file token_utils.py
@brief Token issuance helpers for authentication flows.

Creates access + refresh token pairs. Used by :mod:`app.services.auth_service`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_token,
)
from app.models.user import User
from app.repositories.token_repo import TokenRepository


async def issue_tokens(
    token_repo: TokenRepository,
    user: User,
    settings: Settings,
    *,
    family_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """
    @brief Create an access token + opaque refresh token pair.

    @param token_repo Token repository for storing refresh tokens.
    @param user The authenticated user ORM instance.
    @param settings Application settings.
    @param family_id Optional token family UUID (for rotation chains).
    @param ip_address Client IP for audit logging.
    @param user_agent Client User-Agent for audit logging.
    @return Dict with token data and raw_refresh_token.
    """
    access = create_access_token(
        user.id,
        extra_claims={"role": user.role, "community_id": str(user.community_id)},
        settings=settings,
    )
    raw_refresh = generate_refresh_token()
    fid = family_id or uuid.uuid4()
    expires = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    await token_repo.create(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        family_id=fid,
        expires_at=expires,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return {
        "access_token": access,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "raw_refresh_token": raw_refresh,
        "requires_2fa": False,
    }
