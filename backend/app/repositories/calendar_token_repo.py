"""@file calendar_token_repo.py
@brief Issue/verify/revoke read-only calendar tokens (sha256-hashed at rest).
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar_token import CalendarToken


def _hash(raw: str) -> str:
    """@brief Hash a raw token using SHA256."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CalendarTokenRepository:
    """@brief Repository for managing calendar access tokens."""

    def __init__(self, session: AsyncSession) -> None:
        """@brief Initialize with async session.
        @param session AsyncSession for database operations.
        """
        self._session = session

    async def issue(self, *, user_id: uuid.UUID, scope: str) -> tuple[str, CalendarToken]:
        """@brief Create and return a new calendar token.
        @param user_id UUID of token owner.
        @param scope Token scope (e.g. 'ical').
        @return Tuple of (raw_token, CalendarToken model).
        """
        raw = secrets.token_urlsafe(32)
        model = CalendarToken(user_id=user_id, token_hash=_hash(raw), scope=scope)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return raw, model

    async def verify(self, raw: str) -> CalendarToken | None:
        """@brief Retrieve token by raw value (non-revoked).
        @param raw Raw token string.
        @return CalendarToken model or None if not found/revoked.
        """
        stmt = select(CalendarToken).where(
            CalendarToken.token_hash == _hash(raw),
            CalendarToken.revoked_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token_id: uuid.UUID) -> None:
        """@brief Revoke a token by setting revoked_at.
        @param token_id UUID of token to revoke.
        """
        await self._session.execute(
            update(CalendarToken)
            .where(CalendarToken.id == token_id)
            .values(revoked_at=datetime.now(UTC))
        )
