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
from typing import Any

from sqlalchemy import bindparam, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import ColumnElement

from app.models.event import Event
from app.models.post import Comment, Post
from app.models.user import User
from app.repositories.base import BaseRepository


def _websearch_tsquery() -> ColumnElement[Any]:
    """
    @brief Build a websearch_to_tsquery expression bound to parameter 'q'.

    websearch_to_tsquery handles raw user input directly -- including
    quoted phrases, stop words, hyphens, and special characters -- without
    requiring manual sanitization.
    """
    return func.websearch_to_tsquery("english", bindparam("q"))


def _prefix_tsquery() -> ColumnElement[Any]:
    """
    @brief Build a to_tsquery expression bound to parameter 'q_prefix'.

    Uses the :* operator on each term so that partial words match stemmed
    lexemes in the GIN index (e.g. "app:*" matches "appl" from "apple").
    """
    return func.to_tsquery("english", bindparam("q_prefix"))


def _fts_expressions(
    fts_col: Any, prefix_query: str | None
) -> tuple[Any, Any, dict[str, str]]:
    """
    @brief Build FTS match expression, rank expression, and bind-param dict.

    When a non-empty *prefix_query* is supplied the WHERE clause uses OR
    to match either the websearch (stemmed full-word) or prefix query, and
    ranking uses GREATEST of both strategies.

    @param fts_col       The TSVECTOR column to match against.
    @param prefix_query  Prefix tsquery string or empty/None.
    @return Tuple of (match_expr, rank_expr, extra_params).
    """
    tsq_ws = _websearch_tsquery()

    if prefix_query:
        tsq_pf = _prefix_tsquery()
        match = fts_col.op("@@")(tsq_ws) | fts_col.op("@@")(tsq_pf)
        rank = func.greatest(
            func.ts_rank(fts_col, tsq_ws),
            func.ts_rank(fts_col, tsq_pf),
        )
        return match, rank, {"q_prefix": prefix_query}

    match = fts_col.op("@@")(tsq_ws)
    rank = func.ts_rank(fts_col, tsq_ws)
    return match, rank, {}


class SearchRepository:
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
    ) -> tuple[list[tuple[Post, float]], str | None, int]:
        """
        @brief Search posts by content using FTS with prefix support.

        @param query        Raw search string from the user.
        @param prefix_query Prefix tsquery string (may be empty).
        @param community_id Community scope.
        @param viewer_id    Current user (for block filter).
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
        stmt = BaseRepository.apply_block_filter(stmt, viewer_id)
        stmt = stmt.order_by(rank_expr.desc(), Post.created_at.desc())

        count_stmt = (
            select(func.count())
            .select_from(Post)
            .where(Post.community_id == community_id)
            .where(Post.deleted_at.is_(None))
            .where(match_expr)
        )
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

    async def search_comments(
        self,
        query: str,
        prefix_query: str,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[tuple[Comment, float]], str | None, int]:
        """
        @brief Search comments by content using FTS with prefix support.

        @param query        Raw search string from the user.
        @param prefix_query Prefix tsquery string (may be empty).
        @param community_id Community scope.
        @param viewer_id    Current user (for block filter).
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
            Comment.content_fts,
            prefix_query,
        )
        params = {"q": query, **extra}

        stmt = (
            select(Comment, rank_expr.label("rank"))
            .where(Comment.community_id == community_id)
            .where(match_expr)
        )
        stmt = BaseRepository.apply_block_filter(stmt, viewer_id)
        stmt = stmt.order_by(
            rank_expr.desc(),
            Comment.created_at.desc(),
        )

        count_stmt = (
            select(func.count())
            .select_from(Comment)
            .where(Comment.community_id == community_id)
            .where(match_expr)
        )
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
