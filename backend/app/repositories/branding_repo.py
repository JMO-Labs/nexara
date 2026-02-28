"""
@file branding_repo.py
@brief Repository for community branding (single-row UPSERT pattern).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branding import CommunityBranding
from app.repositories.base import BaseRepository


class BrandingRepository(BaseRepository[CommunityBranding]):
    """
    @brief Async repository for community branding data.

    The branding table has exactly one row per community.  ``get()``
    returns defaults when no row exists; ``upsert()`` inserts or updates.
    """

    model = CommunityBranding

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, community_id: uuid.UUID) -> CommunityBranding | None:
        """
        @brief Fetch the branding row for a community.

        @param community_id UUID of the community.
        @return The CommunityBranding instance, or None if not yet created.
        """
        stmt = select(CommunityBranding).where(
            CommunityBranding.community_id == community_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        community_id: uuid.UUID,
        data: dict[str, Any],
    ) -> CommunityBranding:
        """
        @brief Insert or update the branding row for a community.

        @param community_id UUID of the community.
        @param data Dict of branding fields to set.
        @return The persisted CommunityBranding instance.
        """
        existing = await self.get(community_id)
        if existing is None:
            branding = CommunityBranding(community_id=community_id, **data)
            self._session.add(branding)
            await self._session.flush()
            await self._session.refresh(branding)
            return branding

        for key, value in data.items():
            if hasattr(existing, key) and value is not None:
                setattr(existing, key, value)
        await self._session.flush()
        await self._session.refresh(existing)
        return existing
