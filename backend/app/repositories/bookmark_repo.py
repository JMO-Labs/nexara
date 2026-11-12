"""
@file bookmark_repo.py
@brief Data access for post bookmarks.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, delete, or_, select

from app.models.bookmark import Bookmark
from app.models.moderation import UserBlock
from app.models.post import Post
from app.models.subgroup import SubgroupMember
from app.repositories.base import BaseRepository
from app.repositories.post_enrichment import enrich_posts


class BookmarkRepository(BaseRepository[Bookmark]):
    """@brief Repository for bookmarks (hard-deleted; cascade on post delete)."""

    model = Bookmark

    async def get_for_user_post(
        self, user_id: uuid.UUID, post_id: uuid.UUID, community_id: uuid.UUID
    ) -> Bookmark | None:
        """@brief Find a user's bookmark for a post. @return Bookmark or None."""
        stmt = select(Bookmark).where(
            Bookmark.user_id == user_id,
            Bookmark.post_id == post_id,
            Bookmark.community_id == community_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create_bookmark(
        self, user_id: uuid.UUID, post_id: uuid.UUID, community_id: uuid.UUID
    ) -> Bookmark:
        """@brief Insert a bookmark. @return The created Bookmark."""
        return await self.create(
            Bookmark(user_id=user_id, post_id=post_id, community_id=community_id)
        )

    async def delete_bookmark(self, bookmark: Bookmark) -> None:
        """@brief Hard-delete a bookmark."""
        await self._session.execute(delete(Bookmark).where(Bookmark.id == bookmark.id))
        await self._session.flush()

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        community_id: uuid.UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[tuple[Bookmark, dict[str, Any]]], str | None]:
        """
        @brief List a user's bookmarks newest first; soft-deleted, blocked and
               no-longer-visible posts are excluded.
        @param cursor ISO timestamp of the last bookmark seen.
        @return (rows of (Bookmark, enriched post dict), next cursor or None).
        """
        member_sgs = select(SubgroupMember.subgroup_id).where(SubgroupMember.user_id == user_id)
        stmt = (
            select(Bookmark)
            .join(Post, Post.id == Bookmark.post_id)
            .where(
                Bookmark.user_id == user_id,
                Bookmark.community_id == community_id,
                Post.deleted_at.is_(None),
                or_(
                    and_(Post.visibility == "community", Post.subgroup_id.is_(None)),
                    and_(Post.visibility == "subgroup", Post.subgroup_id.in_(member_sgs)),
                    and_(Post.visibility == "private", Post.author_id == user_id),
                ),
            )
            .order_by(Bookmark.created_at.desc(), Bookmark.id.desc())
        )
        blocked = select(UserBlock.id).where(
            or_(
                and_(UserBlock.blocker_id == user_id, UserBlock.blocked_id == Post.author_id),
                and_(UserBlock.blocked_id == user_id, UserBlock.blocker_id == Post.author_id),
            )
        )
        stmt = stmt.where(~blocked.exists())
        if cursor:
            try:
                stmt = stmt.where(Bookmark.created_at < datetime.fromisoformat(cursor))
            except ValueError:
                pass
        rows = list((await self._session.execute(stmt.limit(limit + 1))).scalars().all())
        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = rows[-1].created_at.isoformat()
        enriched = await enrich_posts(self._session, [b.post_id for b in rows], user_id)
        return [(b, enriched[b.post_id]) for b in rows if b.post_id in enriched], next_cursor
