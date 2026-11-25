"""
@file community_service.py
@brief Community creation.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import Community


class CommunityService:
    """
    @brief Creates communities.

    @param session Async DB session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_community(self, name: str, owner_id: uuid.UUID) -> Community:
        """
        @brief Persist a community.

        @param name Community display name.
        @param owner_id User who created the community.
        @return The created Community.
        """
        community = Community(name=name)
        self._session.add(community)
        await self._session.flush()
        await self._session.refresh(community)
        return community
