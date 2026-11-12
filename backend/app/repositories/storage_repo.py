"""
@file storage_repo.py
@brief Read-only queries for storage snapshots and per-user usage.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.retention import StorageSnapshot
from app.models.user import User


class StorageRepository:
    """@brief Storage analytics queries (snapshots are instance-wide)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def snapshots_since(self, days: int) -> list[StorageSnapshot]:
        """@brief Snapshots from the last ``days`` days, oldest first."""
        since = date.today() - timedelta(days=days)
        stmt = (
            select(StorageSnapshot)
            .where(StorageSnapshot.snapshot_date >= since)
            .order_by(StorageSnapshot.snapshot_date.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    def _users(self, community_id: uuid.UUID):  # noqa: ANN202
        return select(User).where(User.community_id == community_id, User.deleted_at.is_(None))

    async def top_users(self, community_id: uuid.UUID, limit: int) -> list[User]:
        """@brief Users with the highest storage_used."""
        stmt = self._users(community_id).order_by(User.storage_used.desc(), User.id).limit(limit)
        return list((await self._session.execute(stmt)).scalars().all())

    async def user_page(
        self, community_id: uuid.UUID, *, offset: int, limit: int
    ) -> tuple[list[User], int]:
        """@brief One page of users by usage desc, plus total user count."""
        base = self._users(community_id)
        total = (
            await self._session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = base.order_by(User.storage_used.desc(), User.id).offset(offset).limit(limit)
        return list((await self._session.execute(stmt)).scalars().all()), int(total)

    async def total_user_bytes(self, community_id: uuid.UUID) -> int:
        """@brief Sum of storage_used across community users."""
        stmt = select(func.coalesce(func.sum(User.storage_used), 0)).where(
            User.community_id == community_id, User.deleted_at.is_(None)
        )
        return int((await self._session.execute(stmt)).scalar_one())
