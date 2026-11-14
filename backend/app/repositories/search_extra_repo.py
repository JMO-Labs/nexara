"""
@file search_extra_repo.py
@brief Gallery and poll search methods, mixed into SearchRepository.

Kept separate from search_repo.py to respect the file-length limit.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gallery import Gallery
from app.models.moderation import UserBlock
from app.models.poll import Poll
from app.models.post import Post
from app.models.subgroup import SubgroupMember


def _offset(cursor: str | None) -> int:
    """@brief Parse an offset cursor, defaulting to 0 when invalid."""
    try:
        return int(cursor) if cursor else 0
    except ValueError:
        return 0


class GalleryPollSearchMixin:
    """@brief Provides search_galleries and search_polls."""

    _session: AsyncSession

    async def search_galleries(
        self,
        query: str,
        prefix_query: str,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[tuple[Gallery, float]], str | None, int]:
        """
        @brief Search galleries by title/description using FTS.

        Visibility: community galleries for all; private only for the owner;
        subgroup galleries only for members of that subgroup.

        @return Tuple of (items with rank, next_cursor, total).
        """
        from app.repositories.search_fts import _fts_expressions

        if not query or not query.strip():
            return [], None, 0
        offset = _offset(cursor)
        match_expr, rank_expr, extra = _fts_expressions(Gallery.search_fts, prefix_query)
        params = {"q": query, **extra}

        member_subq = select(SubgroupMember.subgroup_id).where(SubgroupMember.user_id == viewer_id)
        visibility = or_(
            Gallery.visibility == "community",
            and_(Gallery.visibility == "private", Gallery.owner_id == viewer_id),
            and_(Gallery.visibility == "subgroup", Gallery.subgroup_id.in_(member_subq)),
        )
        stmt = (
            select(Gallery, rank_expr.label("rank"))
            .where(Gallery.community_id == community_id, visibility, match_expr)
            .order_by(rank_expr.desc(), Gallery.created_at.desc())
        )
        count_stmt = (
            select(func.count())
            .select_from(Gallery)
            .where(Gallery.community_id == community_id, visibility, match_expr)
        )
        rows, next_cursor, total = await self._run(stmt, count_stmt, params, offset, limit)
        return [(r[0], r[1]) for r in rows], next_cursor, total

    async def search_polls(
        self,
        query: str,
        prefix_query: str,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        cursor: str | None,
        limit: int,
        include_nsfw: bool = False,
    ) -> tuple[list[tuple[Poll, Post, float]], str | None, int]:
        """
        @brief Search polls via the FTS content of the post they are attached to.

        Applies the post's soft-delete, visibility, and block rules. Polls on
        NSFW posts are excluded unless *include_nsfw* (adult viewers only).

        @return Tuple of ((poll, post, rank) items, next_cursor, total).
        """
        from app.repositories.search_fts import _fts_expressions

        if not query or not query.strip():
            return [], None, 0
        offset = _offset(cursor)
        match_expr, rank_expr, extra = _fts_expressions(Post.content_fts, prefix_query)
        params = {"q": query, **extra}

        member_subq = select(SubgroupMember.subgroup_id).where(SubgroupMember.user_id == viewer_id)
        visibility = or_(
            Post.visibility == "community",
            and_(Post.visibility == "private", Post.author_id == viewer_id),
            and_(Post.visibility == "subgroup", Post.subgroup_id.in_(member_subq)),
        )
        blocked = (
            select(UserBlock.id)
            .where(
                or_(
                    and_(UserBlock.blocker_id == viewer_id, UserBlock.blocked_id == Post.author_id),
                    and_(UserBlock.blocker_id == Post.author_id, UserBlock.blocked_id == viewer_id),
                )
            )
            .exists()
        )
        conds: list[Any] = [
            Poll.community_id == community_id,
            Post.deleted_at.is_(None),
            Poll.deleted_at.is_(None),
            visibility,
            ~blocked,
            match_expr,
        ]
        if not include_nsfw:
            conds.append(Post.is_nsfw.is_(False))
        stmt = (
            select(Poll, Post, rank_expr.label("rank"))
            .join(Post, Post.id == Poll.post_id)
            .where(*conds)
            .order_by(rank_expr.desc(), Poll.created_at.desc())
        )
        count_stmt = (
            select(func.count()).select_from(Poll).join(Post, Post.id == Poll.post_id).where(*conds)
        )
        rows, next_cursor, total = await self._run(stmt, count_stmt, params, offset, limit)
        return [(r[0], r[1], r[2]) for r in rows], next_cursor, total

    async def _run(
        self, stmt: Any, count_stmt: Any, params: dict[str, str], offset: int, limit: int
    ) -> tuple[list[Any], str | None, int]:
        """@brief Execute a paged query plus count; returns (rows, next_cursor, total)."""
        result = await self._session.execute(stmt.offset(offset).limit(limit + 1), params)
        rows = list(result.all())
        total = (await self._session.execute(count_stmt, params)).scalar_one()
        next_cursor = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = str(offset + limit)
        return rows, next_cursor, total
