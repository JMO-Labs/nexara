"""
@file nsfw_cascade.py
@brief A moderator/admin NSFW flag on a post or album also flags and locks the
       photos inside it at the same level, so a photo moved out stays NSFW.
       Unflagging at that level clears exactly the photo locks at that level.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gallery import GalleryItem
from app.models.media import Media
from app.models.post import PostMedia


def _contained(kind: str, entity_id: uuid.UUID) -> Any:
    """@brief Media ids inside the post or album."""
    if kind == "posts":
        return select(PostMedia.media_id).where(PostMedia.post_id == entity_id)
    return select(GalleryItem.media_id).where(GalleryItem.gallery_id == entity_id)


async def cascade_media_lock(
    session: AsyncSession,
    kind: str,
    entity_id: uuid.UUID,
    community_id: uuid.UUID,
    *,
    value: bool,
    level: str | None,
) -> None:
    """
    @brief Mirror a container flag change onto its photos.
    @param kind "posts" or "galleries" (other kinds are ignored).
    @param value New container flag.
    @param level Setting: the container's lock level (never downgrades a stronger
           photo lock). Clearing: the level the container held (None = nothing to clear).
    """
    if kind not in ("posts", "galleries") or level is None:
        return
    scope = (Media.id.in_(_contained(kind, entity_id)), Media.community_id == community_id)
    if value:
        weaker = or_(Media.nsfw_lock_level.is_(None), Media.nsfw_lock_level == level)
        if level == "admin":
            weaker = or_(weaker, Media.nsfw_lock_level == "moderator")
        stmt = update(Media).where(*scope, weaker).values(is_nsfw=True, nsfw_lock_level=level)
    else:
        stmt = (
            update(Media)
            .where(*scope, Media.nsfw_lock_level == level)
            .values(is_nsfw=False, nsfw_lock_level=None)
        )
    await session.execute(stmt, execution_options={"synchronize_session": False})
