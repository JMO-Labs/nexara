"""
@file moderation_repo.py
@brief Repository for moderation flags (NSFW) on posts and media.
"""

from __future__ import annotations

import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import Media
from app.models.post import Post

_MODELS = {"post": Post, "media": Media}


class ModerationRepository:
    """
    @brief Async repository toggling moderation flags.

    @param session Async SQLAlchemy session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def set_nsfw(
        self, kind: str, target_id: uuid.UUID, community_id: uuid.UUID, value: bool
    ) -> bool:
        """
        @brief Set is_nsfw on a non-deleted post or media row.

        @param kind         "post" or "media".
        @param target_id    Row UUID.
        @param community_id Community scope.
        @param value        New flag value.
        @return True when a row was updated.
        """
        model = _MODELS[kind]
        stmt = (
            update(model)
            .where(model.id == target_id, model.community_id == community_id)
            .values(is_nsfw=value)
        )
        if hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        await self._session.flush()
        return bool(result.rowcount)  # type: ignore[attr-defined]
