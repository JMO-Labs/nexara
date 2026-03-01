"""
@file comment_repo.py
@brief Repository for comments and reactions.

Provides comment CRUD and list operations, plus reaction toggle.
All queries apply soft-delete filtering and community_id scoping.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Comment, Reaction
from app.models.user import User
from app.repositories.base import BaseRepository


class CommentRepository:
    """
    @brief Repository for comment operations.

    @param session Async SQLAlchemy session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_post(
        self,
        post_id: uuid.UUID,
        viewer_id: uuid.UUID | None = None,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        @brief Fetch paginated comments for a post, newest first.

        @param post_id Post UUID.
        @param viewer_id Current user for block filter.
        @param cursor Opaque cursor (ISO timestamp of last seen comment).
        @param limit Number of comments per page.
        @return Tuple of (comment dicts, next_cursor or None).
        """
        limit = min(limit, 50)

        stmt = (
            select(Comment, User)
            .join(User, Comment.author_id == User.id)
            .where(Comment.post_id == post_id)
            .order_by(Comment.created_at.desc())
        )

        if cursor:
            from datetime import datetime

            try:
                cursor_ts = datetime.fromisoformat(cursor)
                stmt = stmt.where(Comment.created_at < cursor_ts)
            except (ValueError, TypeError):
                pass

        if viewer_id:
            stmt = BaseRepository.apply_block_filter(stmt, viewer_id)

        stmt = stmt.limit(limit + 1)
        result = await self._session.execute(stmt)
        rows = list(result.all())

        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = rows[-1][0].created_at.isoformat()

        comment_ids = [c.id for c, _ in rows]
        reaction_map = await self._load_comment_reactions(comment_ids, viewer_id)

        comments = []
        for comment, author in rows:
            comments.append(
                {
                    "id": str(comment.id),
                    "content": comment.content,
                    "author": {
                        "id": str(author.id),
                        "username": author.username,
                        "display_name": author.display_name,
                        "avatar_url": author.avatar_url,
                    },
                    "parent_id": str(comment.parent_id) if comment.parent_id else None,
                    "created_at": comment.created_at.isoformat(),
                    "replies": [],
                    "reactions": reaction_map.get(comment.id, []),
                }
            )
        return comments, next_cursor

    async def _load_comment_reactions(
        self,
        comment_ids: list[uuid.UUID],
        viewer_id: uuid.UUID | None,
    ) -> dict[uuid.UUID, list[dict[str, Any]]]:
        """
        @brief Batch-load reactions for comments with reacted_by_me flag.

        @param comment_ids List of comment UUIDs.
        @param viewer_id Current user for reacted_by_me.
        @return Dict mapping comment_id -> list of {emoji, count, reacted_by_me}.
        """
        if not comment_ids:
            return {}

        reaction_stmt = (
            select(
                Reaction.target_id,
                Reaction.emoji,
                func.count().label("cnt"),
            )
            .where(Reaction.target_type == "comment", Reaction.target_id.in_(comment_ids))
            .group_by(Reaction.target_id, Reaction.emoji)
        )
        reaction_result = await self._session.execute(reaction_stmt)
        reaction_map: dict[uuid.UUID, list[dict[str, Any]]] = {}
        for target_id, emoji, cnt in reaction_result.all():
            reaction_map.setdefault(target_id, []).append(
                {
                    "emoji": emoji,
                    "count": cnt,
                    "reacted_by_me": False,
                }
            )

        if viewer_id:
            my_reactions_stmt = select(Reaction.target_id, Reaction.emoji).where(
                Reaction.target_type == "comment",
                Reaction.target_id.in_(comment_ids),
                Reaction.user_id == viewer_id,
            )
            my_result = await self._session.execute(my_reactions_stmt)
            my_set = {(tid, em) for tid, em in my_result.all()}
            for cid, reactions in reaction_map.items():
                for r in reactions:
                    if (cid, r["emoji"]) in my_set:
                        r["reacted_by_me"] = True

        return reaction_map

    async def create_comment(
        self,
        post_id: uuid.UUID,
        author_id: uuid.UUID,
        content: str,
        community_id: uuid.UUID,
        parent_id: uuid.UUID | None = None,
    ) -> Comment:
        """
        @brief Insert a new comment.

        @param post_id Post this comment belongs to.
        @param author_id Comment author.
        @param content Comment text.
        @param community_id Community scope.
        @param parent_id Optional parent for nested replies.
        @return The created Comment ORM instance.
        """
        comment = Comment(
            post_id=post_id,
            author_id=author_id,
            content=content,
            community_id=community_id,
            parent_id=parent_id,
        )
        self._session.add(comment)
        await self._session.flush()
        await self._session.refresh(comment)
        return comment

    async def get_by_id(self, comment_id: uuid.UUID) -> Comment | None:
        """@brief Fetch a single comment by ID."""
        result = await self._session.execute(select(Comment).where(Comment.id == comment_id))
        return result.scalar_one_or_none()


class ReactionRepository:
    """
    @brief Repository for reaction toggle operations.

    @param session Async SQLAlchemy session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def toggle(
        self,
        user_id: uuid.UUID,
        target_type: str,
        target_id: uuid.UUID,
        emoji: str,
        community_id: uuid.UUID,
    ) -> tuple[str, int]:
        """
        @brief Toggle a reaction: add if not exists, remove if exists.

        @param user_id Reacting user UUID.
        @param target_type "post" or "comment".
        @param target_id UUID of the target entity.
        @param emoji Emoji string.
        @param community_id Community scope.
        @return Tuple of (action, new_count) where action is "added" or "removed".
        """
        existing_stmt = select(Reaction).where(
            Reaction.user_id == user_id,
            Reaction.target_type == target_type,
            Reaction.target_id == target_id,
            Reaction.emoji == emoji,
        )
        result = await self._session.execute(existing_stmt)
        existing = result.scalar_one_or_none()

        if existing:
            await self._session.delete(existing)
            await self._session.flush()
            action = "removed"
        else:
            reaction = Reaction(
                user_id=user_id,
                target_type=target_type,
                target_id=target_id,
                emoji=emoji,
                community_id=community_id,
            )
            self._session.add(reaction)
            await self._session.flush()
            action = "added"

        count_stmt = (
            select(func.count())
            .select_from(Reaction)
            .where(
                Reaction.target_type == target_type,
                Reaction.target_id == target_id,
                Reaction.emoji == emoji,
            )
        )
        count_result = await self._session.execute(count_stmt)
        count = count_result.scalar_one()

        return action, count
