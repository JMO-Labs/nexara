"""
@file post_repo.py
@brief Repository for posts.

Provides cursor-paginated feed queries with author, media, reactions,
and comment counts. All queries apply soft-delete filtering and
community_id scoping.

Enrichment helpers live in post_enrichment.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import and_, func, or_, select

from app.models.media import Media
from app.models.post import Post, PostMedia
from app.repositories.base import BaseRepository
from app.repositories.post_enrichment import enrich_posts

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
        subgroup_id: uuid.UUID | None = None,
        subgroup_ids: list[uuid.UUID] | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        @brief Fetch paginated feed posts with author, media, reactions, and comment count.

        @param community_id Community scope.
        @param viewer_id Current user UUID for block filter, reaction state, and visibility.
        @param cursor Opaque cursor (ISO timestamp of last seen post).
        @param limit Number of posts to return.
        @param subgroup_id Optional single subgroup ID filter (overrides visibility predicate).
        @param subgroup_ids Subgroup IDs the viewer belongs to (for visibility scoping).
        @return Tuple of (enriched post dicts, next_cursor).
        """
        limit = min(limit, MAX_PAGE_SIZE)

        stmt = (
            self._base_query()
            .where(Post.community_id == community_id)
            .order_by(Post.created_at.desc())
        )

        if cursor:
            try:
                cursor_ts = datetime.fromisoformat(cursor)
                stmt = stmt.where(Post.created_at < cursor_ts)
            except (ValueError, TypeError):
                pass

        if subgroup_id is not None:
            stmt = stmt.where(Post.subgroup_id == subgroup_id)
        elif viewer_id is not None:
            allowed = subgroup_ids or []
            if allowed:
                visibility_pred = or_(
                    and_(Post.visibility == "community", Post.subgroup_id.is_(None)),
                    and_(Post.visibility == "subgroup", Post.subgroup_id.in_(allowed)),
                    and_(Post.visibility == "private", Post.author_id == viewer_id),
                )
            else:
                visibility_pred = or_(
                    and_(Post.visibility == "community", Post.subgroup_id.is_(None)),
                    and_(Post.visibility == "private", Post.author_id == viewer_id),
                )
            stmt = stmt.where(visibility_pred)

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

    async def count_new_since(
        self,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        since: Any,
        *,
        subgroup_ids: list[uuid.UUID] | None = None,
    ) -> int:
        """
        @brief Count posts visible to viewer created after ``since``.

        @param community_id Community scope.
        @param viewer_id Viewer UUID for block filter and visibility scoping.
        @param since Datetime cutoff (posts created after this are counted).
        @param subgroup_ids Subgroup IDs the viewer belongs to (for visibility scoping).
        @return Integer count of new posts.
        """
        stmt = (
            select(func.count())
            .select_from(Post)
            .where(Post.community_id == community_id)
            .where(Post.deleted_at.is_(None))
        )
        if isinstance(since, datetime):
            stmt = stmt.where(Post.created_at > since)

        allowed = subgroup_ids or []
        if allowed:
            visibility_pred = or_(
                and_(Post.visibility == "community", Post.subgroup_id.is_(None)),
                and_(Post.visibility == "subgroup", Post.subgroup_id.in_(allowed)),
                and_(Post.visibility == "private", Post.author_id == viewer_id),
            )
        else:
            visibility_pred = or_(
                and_(Post.visibility == "community", Post.subgroup_id.is_(None)),
                and_(Post.visibility == "private", Post.author_id == viewer_id),
            )
        stmt = stmt.where(visibility_pred)

        stmt = self.apply_block_filter(stmt, viewer_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

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
        reply_to_prompt_id: uuid.UUID | None = None,
        subgroup_id: uuid.UUID | None = None,
    ) -> Post:
        """
        @brief Insert a new post row.

        @param author_id Author UUID.
        @param content Markdown content.
        @param community_id Community scope.
        @param reply_to_prompt_id Optional prompt post UUID for reply tracking.
        @param subgroup_id Optional subgroup UUID to scope the post.
        @return The created Post ORM instance.
        """
        post = Post(
            author_id=author_id,
            content=content,
            community_id=community_id,
            reply_to_prompt_id=reply_to_prompt_id,
            subgroup_id=subgroup_id,
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

    async def list_replies_for_prompt(
        self,
        prompt_id: uuid.UUID,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        @brief Fetch posts that are replies to a prompt, with media IDs.

        @param prompt_id Prompt UUID to filter replies.
        @param limit Maximum number of posts to return.
        @return List of dicts with id, visibility, subgroup_id and media_ids.
        """
        stmt = (
            self._base_query()
            .where(Post.reply_to_prompt_id == prompt_id)
            .order_by(Post.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        posts = list(result.scalars().all())

        if not posts:
            return []

        post_ids = [p.id for p in posts]

        media_stmt = (
            select(PostMedia.post_id, Media.id)
            .join(Media, PostMedia.media_id == Media.id)
            .where(PostMedia.post_id.in_(post_ids))
            .order_by(PostMedia.position)
        )
        media_result = await self._session.execute(media_stmt)
        media_map: dict[uuid.UUID, list[uuid.UUID]] = {}
        for pm_post_id, media_id in media_result.all():
            media_map.setdefault(pm_post_id, []).append(media_id)

        return [
            {
                "id": p.id,
                "visibility": p.visibility,
                "subgroup_id": p.subgroup_id,
                "media_ids": media_map.get(p.id, []),
            }
            for p in posts
        ]

    async def exists_many(
        self,
        post_ids: set[uuid.UUID] | list[uuid.UUID],
    ) -> set[uuid.UUID]:
        """
        @brief Batch-check which post IDs exist (soft-delete aware).

        @param post_ids Set or list of post UUIDs to check.
        @return Set of post IDs that exist (not soft-deleted).
        """
        stmt = select(Post.id).where(
            and_(
                Post.id.in_(list(post_ids)),
                Post.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def _enrich_posts(
        self,
        post_ids: list[uuid.UUID],
        viewer_id: uuid.UUID | None,
    ) -> dict[uuid.UUID, dict[str, Any]]:
        """
        @brief Delegate to post_enrichment.enrich_posts.

        @param post_ids List of post UUIDs.
        @param viewer_id Current user for ``reacted_by_me`` flag.
        @return Dict mapping post_id -> enriched dict.
        """
        return await enrich_posts(self._session, post_ids, viewer_id)
