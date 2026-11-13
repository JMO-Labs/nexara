"""
@file search_repo.py
@brief Repository for full-text search across posts, users, events, and comments.

Uses PostgreSQL websearch_to_tsquery for robust user-input handling and
to_tsquery with the :* prefix operator for partial-word matching.
ts_rank with GREATEST is used for relevance ordering across both strategies.
Applies soft-delete and block filters where applicable.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.post import Post
from app.models.user import User
from app.repositories.base import BaseRepository
from app.repositories.search_content_repo import SubgroupCommentSearchMixin
from app.repositories.search_extra_repo import GalleryPollSearchMixin
from app.repositories.search_fts import _fts_expressions, _prefix_tsquery, _websearch_tsquery  # noqa: F401


class SearchRepository(GalleryPollSearchMixin, SubgroupCommentSearchMixin):
    """
    @brief Async repository for full-text search.

    Provides search_posts, search_users, search_events, and search_comments
    using PostgreSQL FTS with both websearch_to_tsquery (full-word stemmed)
    and to_tsquery prefix matching for partial-word support.

    @param session Async SQLAlchemy session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_posts(
        self,
        query: str,
        prefix_query: str,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        cursor: str | None,
        limit: int,
        include_nsfw: bool = False,
    ) -> tuple[list[tuple[Post, float]], str | None, int]:
        """
        @brief Search posts by content using FTS with prefix support.

        @param query        Raw search string from the user.
        @param prefix_query Prefix tsquery string (may be empty).
        @param community_id Community scope.
        @param viewer_id    Current user (for block filter).
        @param cursor       Opaque pagination cursor (offset).
        @param limit        Max items to return.
        @param include_nsfw Include NSFW-flagged posts (adult viewers only).
        @return Tuple of (items with rank, next_cursor, total).
        """
        if not query or not query.strip():
            return [], None, 0

        try:
            offset = int(cursor) if cursor else 0
        except ValueError:
            offset = 0

        match_expr, rank_expr, extra = _fts_expressions(
            Post.content_fts,
            prefix_query,
        )
        params = {"q": query, **extra}

        stmt = (
            select(Post, rank_expr.label("rank"))
            .where(Post.community_id == community_id)
            .where(Post.deleted_at.is_(None))
            .where(match_expr)
        )
        if not include_nsfw:
            stmt = stmt.where(Post.is_nsfw.is_(False))
        stmt = BaseRepository.apply_block_filter(stmt, viewer_id)
        stmt = stmt.order_by(rank_expr.desc(), Post.created_at.desc())

        count_stmt = (
            select(func.count())
            .select_from(Post)
            .where(Post.community_id == community_id)
            .where(Post.deleted_at.is_(None))
            .where(match_expr)
        )
        if not include_nsfw:
            count_stmt = count_stmt.where(Post.is_nsfw.is_(False))
        count_stmt = BaseRepository.apply_block_filter(
            count_stmt,
            viewer_id,
        )

        result = await self._session.execute(
            stmt.offset(offset).limit(limit + 1),
            params,
        )
        rows = result.all()
        count_result = await self._session.execute(count_stmt, params)
        total = count_result.scalar_one()

        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = str(offset + limit)

        return [(r[0], r[1]) for r in rows], next_cursor, total

    async def search_users(
        self,
        query: str,
        prefix_query: str,
        community_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[tuple[User, float]], str | None, int]:
        """
        @brief Search users by display_name, username, bio using FTS.

        @param query        Raw search string from the user.
        @param prefix_query Prefix tsquery string (may be empty).
        @param community_id Community scope.
        @param cursor       Opaque pagination cursor (offset).
        @param limit        Max items to return.
        @return Tuple of (items with rank, next_cursor, total).
        """
        if not query or not query.strip():
            return [], None, 0

        try:
            offset = int(cursor) if cursor else 0
        except ValueError:
            offset = 0

        match_expr, rank_expr, extra = _fts_expressions(
            User.search_fts,
            prefix_query,
        )
        params = {"q": query, **extra}

        stmt = (
            select(User, rank_expr.label("rank"))
            .where(User.community_id == community_id)
            .where(User.deleted_at.is_(None))
            .where(match_expr)
            .order_by(rank_expr.desc(), User.created_at.desc())
        )

        count_stmt = (
            select(func.count())
            .select_from(User)
            .where(User.community_id == community_id)
            .where(User.deleted_at.is_(None))
            .where(match_expr)
        )

        result = await self._session.execute(
            stmt.offset(offset).limit(limit + 1),
            params,
        )
        rows = result.all()
        count_result = await self._session.execute(count_stmt, params)
        total = count_result.scalar_one()

        next_cursor = str(offset + limit) if len(rows) > limit else None
        if len(rows) > limit:
            rows = rows[:limit]

        return [(r[0], r[1]) for r in rows], next_cursor, total

    async def search_events(
        self,
        query: str,
        prefix_query: str,
        community_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[tuple[Event, float]], str | None, int]:
        """
        @brief Search events by title, description, location using FTS.

        @param query        Raw search string from the user.
        @param prefix_query Prefix tsquery string (may be empty).
        @param community_id Community scope.
        @param cursor       Opaque pagination cursor (offset).
        @param limit        Max items to return.
        @return Tuple of (items with rank, next_cursor, total).
        """
        if not query or not query.strip():
            return [], None, 0

        try:
            offset = int(cursor) if cursor else 0
        except ValueError:
            offset = 0

        match_expr, rank_expr, extra = _fts_expressions(
            Event.search_fts,
            prefix_query,
        )
        params = {"q": query, **extra}

        stmt = (
            select(Event, rank_expr.label("rank"))
            .where(Event.community_id == community_id)
            .where(match_expr)
            .order_by(rank_expr.desc(), Event.starts_at.desc())
        )

        count_stmt = (
            select(func.count())
            .select_from(Event)
            .where(Event.community_id == community_id)
            .where(match_expr)
        )

        result = await self._session.execute(
            stmt.offset(offset).limit(limit + 1),
            params,
        )
        rows = result.all()
        count_result = await self._session.execute(count_stmt, params)
        total = count_result.scalar_one()

        next_cursor = str(offset + limit) if len(rows) > limit else None
        if len(rows) > limit:
            rows = rows[:limit]

        return [(r[0], r[1]) for r in rows], next_cursor, total
