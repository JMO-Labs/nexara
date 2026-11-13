"""
@file community_repo.py
@brief Repository for the ``Community`` row (tenant-level settings).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import Community

#: Columns an admin may change through the AI tab.
SASSYBOT_COLUMNS = frozenset(
    {"sassybot_enabled", "sassybot_sass_level", "sassybot_probability", "sassybot_invoke_only"}
)


class CommunityRepository:
    """@brief Reads/updates the community row; always keyed by ``community_id``."""

    def __init__(self, session: AsyncSession) -> None:
        """@param session Async DB session."""
        self._session = session

    async def get(self, community_id: uuid.UUID) -> Community | None:
        """
        @param community_id Tenant id.
        @return The community or None.
        """
        return await self._session.get(Community, community_id)

    async def update_sassybot(
        self, community_id: uuid.UUID, values: dict[str, Any]
    ) -> Community | None:
        """
        @brief Update Sassybot columns of one community.
        @param community_id Tenant id.
        @param values Column -> value; keys must be in ``SASSYBOT_COLUMNS``.
        @return The refreshed community, or None if it does not exist.
        @throws ValueError on an unknown column.
        """
        unknown = set(values) - SASSYBOT_COLUMNS
        if unknown:
            raise ValueError(f"Unknown Sassybot column(s): {sorted(unknown)}")
        community = await self.get(community_id)
        if community is None:
            return None
        for key, value in values.items():
            setattr(community, key, value)
        await self._session.flush()
        await self._session.refresh(community)
        return community
