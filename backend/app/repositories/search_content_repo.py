"""
@file search_content_repo.py
@brief Subgroup and comment search mixin.

Split from search_repo.py.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Comment
from app.models.subgroup import Subgroup
from app.repositories.base import BaseRepository
from app.repositories.search_fts import _exclude_nsfw_comments, _fts_expressions


class SubgroupCommentSearchMixin:
    """@brief Mixin providing search_subgroups and search_comments."""

    _session: AsyncSession

    async def search_subgroups(
        self,
        query: str,
        prefix_query: str,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[tuple[Subgroup, float]], str | None, int]:
        """
        @brief Search subgroups by name/description using FTS.

        Excludes archived. Private subgroups only included if viewer is a member.
        """
        if not query or not query.strip():
            return [], None, 0

        try:
            offset = int(cursor) if cursor else 0
        except ValueError:
            offset = 0

        match_expr, rank_expr, extra = _fts_expressions(
            Subgroup.search_fts,
            prefix_query,
        )
        params = {"q": query, **extra}

        from app.repositories.subgroup_repo import visible_subgroup_ids_subq

        visibility = (Subgroup.is_private.is_(False)) | (
            Subgroup.id.in_(visible_subgroup_ids_subq(viewer_id))
        )

        stmt = (
            select(Subgroup, rank_expr.label("rank"))
            .where(Subgroup.community_id == community_id)
            .where(Subgroup.archived_at.is_(None))
            .where(visibility)
            .where(match_expr)
            .order_by(rank_expr.desc(), Subgroup.created_at.desc())
        )

        count_stmt = (
            select(func.count())
            .select_from(Subgroup)
            .where(Subgroup.community_id == community_id)
            .where(Subgroup.archived_at.is_(None))
            .where(visibility)
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
        include_nsfw: bool = False,
    ) -> tuple[list[tuple[Comment, float]], str | None, int]:
        """
        @brief Search comments by content using FTS with prefix support.

        @param query        Raw search string from the user.
        @param prefix_query Prefix tsquery string (may be empty).
        @param community_id Community scope.
        @param viewer_id    Current user (for block filter).
        @param cursor       Opaque pagination cursor (offset).
        @param limit        Max items to return.
        @param include_nsfw Include comments on NSFW posts (adult viewers only).
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
        if not include_nsfw:
            stmt = _exclude_nsfw_comments(stmt)
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
        if not include_nsfw:
            count_stmt = _exclude_nsfw_comments(count_stmt)
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
