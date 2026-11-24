"""
@file nsfw_cascade.py
@brief A moderator/admin NSFW flag on a post or album reaches the photos inside
       it through ``media_nsfw_sources`` rows, so a photo moved out stays NSFW
       (and locked at that level). Unflagging removes only that container's
       rows; the photo's own flag and other containers' rows are untouched.

A non-admin moderator's flag only reaches photos the container's author/owner
uploaded (they could not otherwise flag someone else's photo used elsewhere).
Effective NSFW = own ``is_nsfw`` OR any source row (``media_is_nsfw``);
effective lock = max(own lock, source levels).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, literal, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gallery import Gallery, GalleryItem
from app.models.media import Media
from app.models.media_nsfw_source import MediaNsfwSource
from app.models.post import Post, PostMedia

_SOURCE = {"posts": "post", "galleries": "gallery"}


async def cascade_media_lock(
    session: AsyncSession,
    kind: str,
    entity_id: uuid.UUID,
    community_id: uuid.UUID,
    *,
    value: bool,
    level: str,
    actor_admin: bool,
) -> None:
    """
    @brief Add (flag) or remove (unflag) this container's source rows.
    @param kind "posts" or "galleries" (other kinds are ignored).
    @param level The container's lock level after the change.
    @param actor_admin Admins reach every photo inside; moderators only the
           author's/owner's own uploads.
    """
    source = _SOURCE.get(kind)
    if source is None:
        return
    rows = MediaNsfwSource
    if not value:
        await session.execute(
            delete(rows).where(rows.source_kind == source, rows.source_id == entity_id)
        )
        return
    if kind == "posts":
        owner: Any = Post.author_id
        stmt = select(PostMedia.media_id).join(Post, Post.id == PostMedia.post_id)
        stmt = stmt.where(PostMedia.post_id == entity_id)
        stmt = stmt.join(Media, Media.id == PostMedia.media_id)
    else:
        owner = Gallery.owner_id
        stmt = select(GalleryItem.media_id).join(Gallery, Gallery.id == GalleryItem.gallery_id)
        stmt = stmt.where(GalleryItem.gallery_id == entity_id)
        stmt = stmt.join(Media, Media.id == GalleryItem.media_id)
    stmt = stmt.where(Media.community_id == community_id)
    if not actor_admin:
        stmt = stmt.where(Media.uploader_id == owner)
    picked = stmt.add_columns(
        literal(source), literal(entity_id), literal(community_id), literal(level)
    )
    ins = insert(rows).from_select(
        ["media_id", "source_kind", "source_id", "community_id", "level"], picked
    )
    ins = ins.on_conflict_do_update(
        index_elements=["media_id", "source_kind", "source_id"], set_={"level": level}
    )
    await session.execute(ins)


async def clear_media_sources(session: AsyncSession, media_id: uuid.UUID) -> None:
    """@brief Admin unflag of a photo: drop every container source on it too."""
    await session.execute(delete(MediaNsfwSource).where(MediaNsfwSource.media_id == media_id))
