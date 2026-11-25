"""
@file signin_repo.py
@brief Repository for sign-in events (append, failure counts, device history, purge).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, String, cast, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signin_event import SigninEvent
from app.models.user import User

Row = tuple[SigninEvent, str | None]
"""@brief (event, username-or-None) result row."""


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

    def _filtered(
        self,
        community_id: uuid.UUID,
        q: str | None,
        success: bool | None,
        method: str | None,
        since: datetime | None,
    ) -> Select[Any]:
        stmt = (
            select(SigninEvent, User.username)
            .outerjoin(User, User.id == SigninEvent.user_id)
            .where(SigninEvent.community_id == community_id)
        )
        if q:
            like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            stmt = stmt.where(
                or_(
                    SigninEvent.email_tried.ilike(like, escape="\\"),
                    cast(SigninEvent.ip, String).ilike(like, escape="\\"),
                    SigninEvent.device.ilike(like, escape="\\"),
                )
            )
        if success is not None:
            stmt = stmt.where(SigninEvent.success.is_(success))
        if method:
            stmt = stmt.where(SigninEvent.method == method)
        if since:
            stmt = stmt.where(SigninEvent.created_at >= since)
        return stmt.order_by(SigninEvent.created_at.desc(), SigninEvent.id.desc())

    async def search(
        self,
        community_id: uuid.UUID,
        *,
        q: str | None = None,
        success: bool | None = None,
        method: str | None = None,
        since: datetime | None = None,
        after: tuple[datetime, uuid.UUID] | None = None,
        limit: int = 50,
    ) -> list[Row]:
        """
        @brief Newest-first filtered page (keyset on created_at, id).

        @param after Keyset position of the last row already seen.
        @return Up to ``limit`` (event, username) rows.
        """
        stmt = self._filtered(community_id, q, success, method, since)
        if after:
            ts, eid = after
            stmt = stmt.where(
                or_(
                    SigninEvent.created_at < ts,
                    (SigninEvent.created_at == ts) & (SigninEvent.id < eid),
                )
            )
        return [(e, u) for e, u in (await self._session.execute(stmt.limit(limit))).all()]
