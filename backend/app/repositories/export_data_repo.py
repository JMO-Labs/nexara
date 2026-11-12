"""
@file export_data_repo.py
@brief Read-only queries collecting a user's personal data for export.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventAttendance
from app.models.media import Media
from app.models.post import Comment, Post, Reaction
from app.models.serialization import serialize
from app.models.user import User


class ExportDataRepository:
    """@brief Returns serialized rows owned by one user (secrets excluded)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _rows(
        self, model: Any, column: Any, user_id: uuid.UUID, community_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        stmt = select(model).where(column == user_id, model.community_id == community_id)
        result = await self._session.stream_scalars(stmt)
        return [serialize(row) async for row in result]

    async def get_profile(self, user_id: uuid.UUID, community_id: uuid.UUID) -> dict[str, Any]:
        """@brief Profile dict. @raises LookupError If the user is missing."""
        user = await self._session.get(User, user_id)
        if user is None or user.community_id != community_id:
            raise LookupError(f"user {user_id} not found")
        return serialize(user)

    async def list_posts(
        self, user_id: uuid.UUID, community_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """@brief Posts authored by the user."""
        return await self._rows(Post, Post.author_id, user_id, community_id)

    async def list_comments(
        self, user_id: uuid.UUID, community_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """@brief Comments authored by the user."""
        return await self._rows(Comment, Comment.author_id, user_id, community_id)

    async def list_reactions(
        self, user_id: uuid.UUID, community_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """@brief Reactions made by the user."""
        return await self._rows(Reaction, Reaction.user_id, user_id, community_id)

    async def list_events(
        self, user_id: uuid.UUID, community_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """@brief Events created by the user."""
        return await self._rows(Event, Event.author_id, user_id, community_id)

    async def list_rsvps(
        self, user_id: uuid.UUID, community_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """@brief Event RSVPs by the user."""
        return await self._rows(EventAttendance, EventAttendance.user_id, user_id, community_id)

    async def list_media(
        self, user_id: uuid.UUID, community_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """@brief Media uploaded by the user."""
        return await self._rows(Media, Media.uploader_id, user_id, community_id)
