"""
@file post_memories_repo.py
@brief "On this day" queries: posts from the same local month/day in past
       years that the viewer can open right now (same visibility and block
       clauses as the feed), plus reminder bookkeeping.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import extract, func, select

from app.models.notification import Notification
from app.models.post import Post
from app.models.user import User
from app.repositories.base import BaseRepository
from app.repositories.post_enrichment import enrich_posts
from app.repositories.visibility_preds import my_subgroup_ids, post_visible


class PostMemoriesRepository(BaseRepository[Post]):
    """@brief Memory reads over posts; every query is community scoped."""

    model = Post

    async def on_this_day(
        self,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        month: int,
        day: int,
        before_year: int,
        limit: int = 12,
        *,
        tz: str = "UTC",
    ) -> list[dict[str, Any]]:
        """
        @param community_id Community scope.
        @param viewer_id Viewer; visibility and block filters apply.
        @param month Local month to match.
        @param day Local day to match.
        @param before_year Only posts whose local year is < this.
        @param limit Max posts.
        @param tz IANA zone the post timestamps are read in.
        @return Feed-shaped dicts, newest first.
        """
        local = func.timezone(tz, Post.created_at)
        stmt = (
            self._base_query()
            .where(
                post_visible(viewer_id, my_subgroup_ids(viewer_id), community_id),
                extract("month", local) == month,
                extract("day", local) == day,
                extract("year", local) < before_year,
            )
            .order_by(Post.created_at.desc())
            .limit(limit)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        if not rows:
            return []
        data = await enrich_posts(self._session, [p.id for p in rows], viewer_id)
        return [data[p.id] for p in rows if p.id in data]

    async def list_user_tz(self, community_id: uuid.UUID) -> list[tuple[uuid.UUID, str | None]]:
        """@return ``(user_id, timezone)`` for every live user in the community."""
        stmt = select(User.id, User.timezone).where(
            User.community_id == community_id, User.deleted_at.is_(None)
        )
        return [(uid, tz) for uid, tz in (await self._session.execute(stmt)).all()]

    async def notified_since(
        self, community_id: uuid.UUID, user_ids: list[uuid.UUID], since: datetime
    ) -> set[uuid.UUID]:
        """@return Users already sent an ``on_this_day`` notification since ``since``."""
        stmt = select(Notification.user_id).where(
            Notification.community_id == community_id,
            Notification.type == "on_this_day",
            Notification.user_id.in_(user_ids),
            Notification.created_at >= since,
        )
        return set((await self._session.execute(stmt)).scalars().all())
