"""
@file kudos_repo.py
@brief Data access for kudos (posts with a recipient).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import or_, select

from app.core.exceptions import AppError
from app.models.post import Post
from app.models.subgroup import SubgroupMember
from app.models.user import User
from app.repositories.base import BaseRepository


class KudosRepository(BaseRepository[Post]):
    """@brief Repository for kudos stored as posts with ``recipient_id`` set."""

    model = Post

    async def create_kudos(
        self,
        author_id: uuid.UUID,
        recipient_id: uuid.UUID,
        message: str,
        community_id: uuid.UUID,
        subgroup_id: uuid.UUID | None = None,
    ) -> Post:
        """@brief Insert a kudos row. @return The created Post."""
        post = Post(
            author_id=author_id,
            recipient_id=recipient_id,
            content=message,
            community_id=community_id,
            subgroup_id=subgroup_id,
            visibility="subgroup" if subgroup_id else "community",
        )
        return await self.create(post)

    async def list_kudos(
        self,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        *,
        recipient_id: uuid.UUID | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[tuple[Post, User | None]], str | None]:
        """
        @brief List kudos newest first, with block and subgroup visibility applied.

        @param cursor ISO timestamp of the last item seen.
        @return (rows of (Post, recipient User), next cursor or None).
        """
        member_subgroups = select(SubgroupMember.subgroup_id).where(
            SubgroupMember.user_id == viewer_id
        )
        before: datetime | None = None
        if cursor:
            try:
                before = datetime.fromisoformat(cursor)
            except ValueError as exc:
                raise AppError("INVALID_CURSOR", "Invalid pagination cursor", 400) from exc
        # Block filter needs a plain single-entity select (no Join in FROM).
        stmt = self.apply_block_filter(select(Post), viewer_id)
        stmt = (
            stmt.add_columns(User)
            .outerjoin(User, User.id == Post.recipient_id)
            .where(
                Post.community_id == community_id,
                Post.recipient_id.isnot(None),
                Post.deleted_at.is_(None),
                or_(Post.subgroup_id.is_(None), Post.subgroup_id.in_(member_subgroups)),
            )
        )
        if recipient_id is not None:
            stmt = stmt.where(Post.recipient_id == recipient_id)
        if before is not None:
            stmt = stmt.where(Post.created_at < before)
        stmt = stmt.order_by(Post.created_at.desc()).limit(limit + 1)
        rows = [(r[0], r[1]) for r in (await self._session.execute(stmt)).all()]
        next_cursor = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = rows[-1][0].created_at.isoformat()
        return rows, next_cursor
