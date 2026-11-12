"""
@file event_gallery.py
@brief Helpers linking an auto-created gallery to an event.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.gallery import Gallery


async def create_event_gallery(
    session: AsyncSession, community_id: uuid.UUID, owner_id: uuid.UUID, event: Event
) -> uuid.UUID:
    """@brief Create the photo gallery for a new event.

    @param session DB session.
    @param community_id Tenant id.
    @param owner_id Gallery owner (event author).
    @param event The freshly created event.
    @return The new gallery id.
    """
    gallery = Gallery(
        community_id=community_id,
        owner_id=owner_id,
        title=event.title,
        visibility=event.visibility,
        subgroup_id=event.subgroup_id,
        contribution_policy="community",
        event_id=event.id,
        is_event_gallery=True,
    )
    session.add(gallery)
    await session.flush()
    return gallery.id


async def find_event_gallery_id(
    session: AsyncSession, community_id: uuid.UUID, event_id: uuid.UUID
) -> uuid.UUID | None:
    """@brief Return the id of the gallery linked to an event, if any."""
    stmt = (
        select(Gallery.id)
        .where(
            Gallery.community_id == community_id,
            Gallery.event_id == event_id,
            Gallery.is_event_gallery.is_(True),
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()
