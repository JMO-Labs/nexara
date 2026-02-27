"""
@file search_repo.py
@brief Repository for full-text search across posts, users, and events.

Uses PostgreSQL tsvector/tsquery and ts_rank for relevance ordering.
Applies soft-delete and block filters where applicable.
"""

from __future__ import annotations

import uuid

from sqlalchemy import bindparam, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.post import Post
from app.models.user import User
from app.repositories.base import BaseRepository


class SearchRepository:
    """
    @brief Async repository for full-text search.

    Provides search_posts, search_users, and search_events using
    PostgreSQL FTS. Does not inherit BaseRepository (no single model).

    @param session Async SQLAlchemy session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_posts(
        self,
        query_ts: str,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[tuple[Post, float]], str | None, int]:
        """
        @brief Search posts by content using FTS.

        @param query_ts Sanitized tsquery string (e.g. "word1 & word2").
        @param community_id Community scope.
        @param viewer_id Current user (for block filter).
        @param cursor Opaque pagination cursor (offset).
        @param limit Max items to return.
        @return Tuple of (items with rank, next_cursor, total).
        """
        if not query_ts:
            return [], None, 0

        try:
            offset = int(cursor) if cursor else 0
        except ValueError:
            offset = 0
        tsq = func.to_tsquery("english", bindparam("q"))
        rank_expr = func.ts_rank(Post.content_fts, tsq)

        stmt = (
            select(Post, rank_expr.label("rank"))
            .where(Post.community_id == community_id)
            .where(Post.deleted_at.is_(None))
            .where(Post.content_fts.op("@@")(tsq))
        )
        stmt = BaseRepository.apply_block_filter(stmt, viewer_id)
        stmt = stmt.order_by(rank_expr.desc(), Post.created_at.desc())

        count_stmt = (
            select(func.count())
            .select_from(Post)
            .where(Post.community_id == community_id)
            .where(Post.deleted_at.is_(None))
            .where(Post.content_fts.op("@@")(tsq))
        )
        count_stmt = BaseRepository.apply_block_filter(count_stmt, viewer_id)

        result = await self._session.execute(stmt.offset(offset).limit(limit + 1), {"q": query_ts})
        rows = result.all()
        count_result = await self._session.execute(count_stmt, {"q": query_ts})
        total = count_result.scalar_one()

        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = str(offset + limit)

        return [(r[0], r[1]) for r in rows], next_cursor, total

    async def search_users(
        self,
        query_ts: str,
        community_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[tuple[User, float]], str | None, int]:
        """
        @brief Search users by display_name, username, bio using FTS.

        @param query_ts Sanitized tsquery string.
        @param community_id Community scope.
        @param cursor Opaque pagination cursor (offset).
        @param limit Max items to return.
        @return Tuple of (items with rank, next_cursor, total).
        """
        if not query_ts:
            return [], None, 0

        try:
            offset = int(cursor) if cursor else 0
        except ValueError:
            offset = 0
        tsq = func.to_tsquery("english", bindparam("q"))
        rank_expr = func.ts_rank(User.search_fts, tsq)

        stmt = (
            select(User, rank_expr.label("rank"))
            .where(User.community_id == community_id)
            .where(User.deleted_at.is_(None))
            .where(User.search_fts.op("@@")(tsq))
            .order_by(rank_expr.desc(), User.created_at.desc())
        )

        count_stmt = (
            select(func.count())
            .select_from(User)
            .where(User.community_id == community_id)
            .where(User.deleted_at.is_(None))
            .where(User.search_fts.op("@@")(tsq))
        )

        result = await self._session.execute(stmt.offset(offset).limit(limit + 1), {"q": query_ts})
        rows = result.all()
        count_result = await self._session.execute(count_stmt, {"q": query_ts})
        total = count_result.scalar_one()

        next_cursor = str(offset + limit) if len(rows) > limit else None
        if len(rows) > limit:
            rows = rows[:limit]

        return [(r[0], r[1]) for r in rows], next_cursor, total

    async def search_events(
        self,
        query_ts: str,
        community_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[tuple[Event, float]], str | None, int]:
        """
        @brief Search events by title, description, location using FTS.

        @param query_ts Sanitized tsquery string.
        @param community_id Community scope.
        @param cursor Opaque pagination cursor (offset).
        @param limit Max items to return.
        @return Tuple of (items with rank, next_cursor, total).
        """
        if not query_ts:
            return [], None, 0

        try:
            offset = int(cursor) if cursor else 0
        except ValueError:
            offset = 0
        tsq = func.to_tsquery("english", bindparam("q"))
        rank_expr = func.ts_rank(Event.search_fts, tsq)

        stmt = (
            select(Event, rank_expr.label("rank"))
            .where(Event.community_id == community_id)
            .where(Event.search_fts.op("@@")(tsq))
            .order_by(rank_expr.desc(), Event.starts_at.desc())
        )

        count_stmt = (
            select(func.count())
            .select_from(Event)
            .where(Event.community_id == community_id)
            .where(Event.search_fts.op("@@")(tsq))
        )

        result = await self._session.execute(stmt.offset(offset).limit(limit + 1), {"q": query_ts})
        rows = result.all()
        count_result = await self._session.execute(count_stmt, {"q": query_ts})
        total = count_result.scalar_one()

        next_cursor = str(offset + limit) if len(rows) > limit else None
        if len(rows) > limit:
            rows = rows[:limit]

        return [(r[0], r[1]) for r in rows], next_cursor, total
