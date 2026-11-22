"""
@file list_activity_repo.py
@brief Append-only repository for the per-list activity log.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import literal, select, tuple_

from app.models.list_assignment import ListActivity
from app.models.user import User
from app.repositories.base import BaseRepository
from app.repositories.list_keyset import decode_cursor, encode_cursor, parse_dt


class ListActivityRepository(BaseRepository[ListActivity]):
    """@brief Async repo for ListActivity rows (insert + keyset read only)."""

    model = ListActivity

    async def add(
        self,
        community_id: uuid.UUID,
        list_id: uuid.UUID,
        actor_id: uuid.UUID | None,
        action: str,
        item_id: uuid.UUID | None,
        item_title: str,
        target_user_id: uuid.UUID | None,
    ) -> ListActivity:
        """@brief Append one log entry."""
        return await self.create(
            ListActivity(
                community_id=community_id,
                list_id=list_id,
                actor_id=actor_id,
                action=action,
                item_id=item_id,
                item_title=item_title,
                target_user_id=target_user_id,
            )
        )

    async def list_page(
        self,
        community_id: uuid.UUID,
        list_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 30,
    ) -> tuple[list[ListActivity], str | None]:
        """
        @brief Newest-first keyset page of a list's activity.

        @return (entries, next_cursor).
        """
        stmt = select(ListActivity).where(
            ListActivity.community_id == community_id, ListActivity.list_id == list_id
        )
        decoded = decode_cursor(cursor, parse_dt)
        if decoded is not None:
            stmt = stmt.where(
                tuple_(ListActivity.created_at, ListActivity.id)
                < tuple_(literal(decoded[0]), literal(decoded[1]))
            )
        stmt = stmt.order_by(ListActivity.created_at.desc(), ListActivity.id.desc())
        rows = list((await self._session.execute(stmt.limit(limit + 1))).scalars().all())
        nxt = None
        if len(rows) > limit:
            rows = rows[:limit]
            nxt = encode_cursor(rows[-1].created_at, rows[-1].id)
        return rows, nxt

    async def users_by_ids(
        self, community_id: uuid.UUID, ids: Iterable[uuid.UUID]
    ) -> dict[uuid.UUID, User]:
        """@brief Users in the community keyed by id (for display hydration)."""
        wanted = set(ids)
        if not wanted:
            return {}
        stmt = select(User).where(User.id.in_(wanted), User.community_id == community_id)
        return {u.id: u for u in (await self._session.execute(stmt)).scalars().all()}
