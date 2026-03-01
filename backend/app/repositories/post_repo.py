"""
@file post_repo.py
@brief Repository for posts.

Provides cursor-paginated feed queries with author, media, reactions,
and comment counts. All queries apply soft-delete filtering and
community_id scoping.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Comment, Post, PostMedia, Reaction
from app.models.user import User
from app.repositories.base import BaseRepository

logger = structlog.get_logger(__name__)

DEFAULT_PAGE_SIZE = 20
"""@brief Default number of items per page."""

MAX_PAGE_SIZE = 50
"""@brief Maximum items per page."""


class PostRepository(BaseRepository[Post]):
    """
    @brief Async repository for post CRUD with feed pagination.

    @param session Async SQLAlchemy session.
    """

    model = Post

    async def list_feed(
        self,
        community_id: uuid.UUID,
        *,
        viewer_id: uuid.UUID | None = None,
        cursor: str | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        @brief Fetch paginated feed posts with author, media, reactions, and comment count.

        @param community_id Community scope.
        @param viewer_id Current user UUID for block filter and reaction state.
        @param cursor Opaque cursor (ISO timestamp of last seen post).
        @param limit Number of posts to return.
        @return Tuple of (enriched post dicts, next_cursor).
        """
        limit = min(limit, MAX_PAGE_SIZE)

        stmt = (
            self._base_query()
            .where(Post.community_id == community_id)
            .order_by(Post.created_at.desc())
        )

        if cursor:
            from datetime import datetime

            try:
                cursor_ts = datetime.fromisoformat(cursor)
                stmt = stmt.where(Post.created_at < cursor_ts)
            except (ValueError, TypeError):
                pass

        if viewer_id:
            stmt = self.apply_block_filter(stmt, viewer_id)

        stmt = stmt.limit(limit + 1)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = rows[-1].created_at.isoformat()

        if not rows:
            return [], None

        post_ids = [p.id for p in rows]
        posts_data = await self._enrich_posts(post_ids, viewer_id)

        ordered = []
        for post in rows:
            data = posts_data.get(post.id)
            if data:
                ordered.append(data)

        return ordered, next_cursor

    async def get_post_detail(
        self,
        post_id: uuid.UUID,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID | None = None,
    ) -> dict[str, Any] | None:
        """
        @brief Fetch a single post with full enrichment.

        @param post_id Post UUID.
        @param community_id Community scope.
        @param viewer_id Current user for reaction state.
        @return Enriched post dict or None.
        """
        stmt = self._base_query().where(Post.id == post_id, Post.community_id == community_id)
        result = await self._session.execute(stmt)
        post = result.scalar_one_or_none()
        if not post:
            return None

        enriched = await self._enrich_posts([post_id], viewer_id)
        return enriched.get(post_id)

    async def create_post(
        self,
        author_id: uuid.UUID,
        content: str,
        community_id: uuid.UUID,
    ) -> Post:
        """
        @brief Insert a new post row.

        @param author_id Author UUID.
        @param content Markdown content.
        @param community_id Community scope.
        @return The created Post ORM instance.
        """
        post = Post(
            author_id=author_id,
            content=content,
            community_id=community_id,
        )
        return await self.create(post)

    async def update_content(
        self,
        post: Post,
        content: str,
    ) -> Post:
        """
        @brief Update a post's text content.

        @param post The Post ORM instance.
        @param content New markdown content.
        @return The updated Post ORM instance.
        """
        post.content = content
        await self._session.flush()
        await self._session.refresh(post)
        return post

    async def soft_delete_post(
        self,
        post_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> bool:
        """
        @brief Soft-delete a post by ID.

        @param post_id Post UUID.
        @param community_id Community scope.
        @return True if a post was deleted, False if not found.
        """
        post = await self.get_by_id(post_id, community_id=community_id)
        if not post:
            return False
        await self.soft_delete(post)
        return True

    async def _enrich_posts(
        self,
        post_ids: list[uuid.UUID],
        viewer_id: uuid.UUID | None,
    ) -> dict[uuid.UUID, dict[str, Any]]:
        """
        @brief Batch-load authors, media, reactions, and comment counts for posts.

        @param post_ids List of post UUIDs.
        @param viewer_id Current user for `reacted_by_me` flag.
        @return Dict mapping post_id -> enriched dict.
        """
        posts_stmt = (
            select(Post, User).join(User, Post.author_id == User.id).where(Post.id.in_(post_ids))
        )
        posts_result = await self._session.execute(posts_stmt)
        post_rows = posts_result.all()

        from app.models.media import Media

        media_stmt = (
            select(PostMedia.post_id, Media)
            .join(Media, PostMedia.media_id == Media.id)
            .where(PostMedia.post_id.in_(post_ids))
            .order_by(PostMedia.position)
        )
        media_result = await self._session.execute(media_stmt)
        media_map: dict[uuid.UUID, list[dict[str, Any]]] = {}
        for pm_post_id, media in media_result.all():
            media_map.setdefault(pm_post_id, []).append(
                {
                    "id": str(media.id),
                    "url": f"/api/v1/media/{media.id}/file",
                    "thumbnail_url": f"/api/v1/media/{media.id}/thumbnail"
                    if media.thumbnail_key
                    else None,
                    "mime_type": media.content_type,
                    "width": media.width,
                    "height": media.height,
                }
            )

        reaction_stmt = (
            select(
                Reaction.target_id,
                Reaction.emoji,
                func.count().label("cnt"),
            )
            .where(Reaction.target_type == "post", Reaction.target_id.in_(post_ids))
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
                Reaction.target_type == "post",
                Reaction.target_id.in_(post_ids),
                Reaction.user_id == viewer_id,
            )
            my_result = await self._session.execute(my_reactions_stmt)
            my_set = {(tid, em) for tid, em in my_result.all()}
            for pid, reactions in reaction_map.items():
                for r in reactions:
                    if (pid, r["emoji"]) in my_set:
                        r["reacted_by_me"] = True

        comment_stmt = (
            select(Comment.post_id, func.count().label("cnt"))
            .where(Comment.post_id.in_(post_ids))
            .group_by(Comment.post_id)
        )
        comment_result = await self._session.execute(comment_stmt)
        comment_map = {pid: cnt for pid, cnt in comment_result.all()}

        enriched: dict[uuid.UUID, dict[str, Any]] = {}
        for post, author in post_rows:
            enriched[post.id] = {
                "id": str(post.id),
                "content": post.content,
                "author": {
                    "id": str(author.id),
                    "username": author.username,
                    "display_name": author.display_name,
                    "avatar_url": author.avatar_url,
                },
                "media": media_map.get(post.id, []),
                "reactions": reaction_map.get(post.id, []),
                "comment_count": comment_map.get(post.id, 0),
                "created_at": post.created_at.isoformat(),
                "updated_at": post.updated_at.isoformat(),
            }
        return enriched
