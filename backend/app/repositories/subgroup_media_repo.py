"""
@file subgroup_media_repo.py
@brief Repository for aggregated subgroup media queries.

Unions media from posts, galleries, and events within a subgroup.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.gallery import Gallery, GalleryItem
from app.models.media import Media
from app.models.post import Post, PostMedia
from app.repositories.base import BaseRepository


class SubgroupMediaRepository:
    """@brief Repository for aggregated media in a subgroup."""

    def __init__(self, session: AsyncSession) -> None:
        """@brief Initialize with session."""
        self._session = session
        self._base_repo: BaseRepository[Any] = BaseRepository(session)

    async def list_media(
        self,
        *,
        subgroup_id: uuid.UUID,
        viewer_id: uuid.UUID,
        source: str,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        @brief List media aggregated from posts, galleries, and events in a subgroup.

        Uses UNION ALL across three source queries:
          - posts: PostMedia -> Post with subgroup_id
          - galleries: GalleryItem -> Gallery with subgroup_id
          - events: GalleryItem -> Gallery -> Event with subgroup_id

        Pagination by keyset on (created_at DESC, media_id DESC).

        @param subgroup_id Subgroup ID.
        @param viewer_id Requesting user ID (for block filter on posts).
        @param source Filter: 'post', 'gallery', 'event', or 'all'.
        @param cursor Opaque pagination cursor (timestamp:uuid).
        @param limit Max items to return (1-200).
        @return Tuple of (media items, next_cursor).
        """
        limit = min(limit, 200)

        # Parse cursor
        cursor_ts = None
        cursor_id = None
        if cursor:
            try:
                parts = cursor.split(":")
                if len(parts) == 2:
                    cursor_ts = datetime.fromisoformat(parts[0])
                    cursor_id = uuid.UUID(parts[1])
            except (ValueError, TypeError):
                pass

        # Build individual source queries
        queries: list[Any] = []

        # Source 1: Posts
        if source in ("all", "post"):
            post_q = (
                select(
                    Media.id,
                    Media.filename,
                    Media.content_type,
                    Media.storage_key,
                    Media.thumbnail_key,
                    Media.size_bytes,
                    Media.width,
                    Media.height,
                    Media.duration_secs,
                    Media.alt_text,
                    Media.status,
                    Media.created_at,
                    Post.id.label("source_id"),
                    Post.content.label("source_title"),
                    literal("post").label("source"),
                )
                .join(PostMedia, PostMedia.media_id == Media.id)
                .join(Post, Post.id == PostMedia.post_id)
                .where(
                    Post.subgroup_id == subgroup_id,
                    Post.deleted_at.is_(None),
                )
            )
            # Apply block filter by excluding blocked users' posts
            post_q = self._base_repo.apply_block_filter(post_q, viewer_id)
            queries.append(post_q)

        # Source 2: Gallery items (direct subgroup galleries)
        if source in ("all", "gallery"):
            gallery_q = (
                select(
                    Media.id,
                    Media.filename,
                    Media.content_type,
                    Media.storage_key,
                    Media.thumbnail_key,
                    Media.size_bytes,
                    Media.width,
                    Media.height,
                    Media.duration_secs,
                    Media.alt_text,
                    Media.status,
                    GalleryItem.created_at,
                    Gallery.id.label("source_id"),
                    Gallery.title.label("source_title"),
                    literal("gallery").label("source"),
                )
                .join(GalleryItem, GalleryItem.media_id == Media.id)
                .join(Gallery, Gallery.id == GalleryItem.gallery_id)
                .where(Gallery.subgroup_id == subgroup_id)
            )
            queries.append(gallery_q)

        # Source 3: Event-linked galleries
        if source in ("all", "event"):
            event_q = (
                select(
                    Media.id,
                    Media.filename,
                    Media.content_type,
                    Media.storage_key,
                    Media.thumbnail_key,
                    Media.size_bytes,
                    Media.width,
                    Media.height,
                    Media.duration_secs,
                    Media.alt_text,
                    Media.status,
                    GalleryItem.created_at,
                    Event.id.label("source_id"),
                    Event.title.label("source_title"),
                    literal("event").label("source"),
                )
                .join(GalleryItem, GalleryItem.media_id == Media.id)
                .join(Gallery, Gallery.id == GalleryItem.gallery_id)
                .join(Event, Event.id == Gallery.event_id)
                .where(
                    Event.subgroup_id == subgroup_id,
                    Gallery.event_id.isnot(None),
                )
            )
            queries.append(event_q)

        if not queries:
            return [], None

        # Union all
        union_stmt = queries[0]
        for q in queries[1:]:
            union_stmt = union_stmt.union_all(q)

        # Subquery for keyset pagination and ordering
        subq = union_stmt.subquery()

        # Apply keyset pagination
        where_clause: Any = True
        if cursor_ts and cursor_id:
            where_clause = or_(
                and_(subq.c.created_at == cursor_ts, subq.c.id < cursor_id),
                subq.c.created_at < cursor_ts,
            )

        stmt = (
            select(subq)
            .where(where_clause)
            .order_by(subq.c.created_at.desc(), subq.c.id.desc())
            .limit(limit + 1)
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        # Check if more items exist
        has_next = len(rows) > limit
        items = rows[:limit]

        # Build response
        items_data = []
        for row in items:
            items_data.append({
                "media_id": str(row.id),
                "media": {
                    "id": str(row.id),
                    "filename": row.filename,
                    "content_type": row.content_type,
                    "storage_key": row.storage_key,
                    "thumbnail_key": row.thumbnail_key,
                    "size_bytes": row.size_bytes,
                    "width": row.width,
                    "height": row.height,
                    "duration_secs": float(row.duration_secs) if row.duration_secs else None,
                    "alt_text": row.alt_text,
                    "status": row.status,
                    "created_at": row.created_at.isoformat(),
                },
                "source": row.source,
                "source_id": str(row.source_id),
                "source_title": row.source_title,
                "created_at": row.created_at.isoformat(),
            })

        # Build next cursor
        next_cursor = None
        if has_next and items:
            last = items[-1]
            next_cursor = f"{last.created_at.isoformat()}:{last.id}"

        return items_data, next_cursor
