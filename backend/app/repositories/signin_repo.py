"""
@file signin_repo.py
@brief Repository for sign-in events (append, failure counts, device history, purge).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signin_event import SigninEvent


class SigninRepository:
    """@brief Async queries over ``signin_events``; every read is community-scoped."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: SigninEvent) -> SigninEvent:
        """@brief Persist an event (flush + refresh)."""
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def count_failures(self, community_id: uuid.UUID, ip: str, minutes: int = 10) -> int:
        """@return Failed attempts from ``ip`` in the last ``minutes``."""
        since = datetime.now(UTC) - timedelta(minutes=minutes)
        stmt = select(func.count(SigninEvent.id)).where(
            SigninEvent.community_id == community_id,
            SigninEvent.ip == ip,
            SigninEvent.success.is_(False),
            SigninEvent.created_at >= since,
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def has_success_with_device(
        self, community_id: uuid.UUID, user_id: uuid.UUID, device: str, days: int = 90
    ) -> bool:
        """@return True if the user signed in successfully with ``device`` within ``days``."""
        since = datetime.now(UTC) - timedelta(days=days)
        stmt = (
            select(SigninEvent.id)
            .where(
                SigninEvent.community_id == community_id,
                SigninEvent.user_id == user_id,
                SigninEvent.success.is_(True),
                SigninEvent.device == device,
                SigninEvent.created_at >= since,
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None

    async def has_any_success(self, community_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@return True if the user has any recorded successful sign-in."""
        stmt = (
            select(SigninEvent.id)
            .where(
                SigninEvent.community_id == community_id,
                SigninEvent.user_id == user_id,
                SigninEvent.success.is_(True),
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None

    async def purge_older_than(self, days: int) -> int:
        """@brief Delete events older than ``days`` (instance-wide). @return rows deleted."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        res = await self._session.execute(
            delete(SigninEvent).where(SigninEvent.created_at < cutoff)
        )
        return int(res.rowcount or 0)  # type: ignore[attr-defined]
