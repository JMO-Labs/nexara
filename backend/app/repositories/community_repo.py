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

    async def update_amazon(
        self, community_id: uuid.UUID, values: dict[str, str | None]
    ) -> Community | None:
        """
        @brief Update Amazon Creators API columns (secret already encrypted).
        @param values column -> value; keys must start with ``amazon_``
        @throws ValueError on any other column
        """
        if any(not k.startswith("amazon_") for k in values):
            raise ValueError("Only amazon_* columns")
        community = await self.get(community_id)
        if community is None:
            return None
        for key, value in values.items():
            setattr(community, key, value)
        await self._session.flush()
        return community

    async def update_inbound(
        self, community_id: uuid.UUID, values: dict[str, Any]
    ) -> Community | None:
        """
        @brief Update reply-by-email columns (password already encrypted).
        @param values column -> value; keys must start with ``inbound_``
        @throws ValueError on any other column
        """
        if any(not k.startswith("inbound_") for k in values):
            raise ValueError("Only inbound_* columns")
        community = await self.get(community_id)
        if community is None:
            return None
        for key, value in values.items():
            setattr(community, key, value)
        await self._session.flush()
        return community

    async def update_features(
        self, community_id: uuid.UUID, patch: dict[str, bool]
    ) -> dict[str, Any]:
        """
        @brief Merge ``patch`` into ``communities.features``.
        @param patch Partial ``{key: bool}``.
        @return The stored features dict ({} if the community is missing).
        """
        community = await self.get(community_id)
        if community is None:
            return {}
        community.features = {**(community.features or {}), **patch}
        await self._session.flush()
        return community.features

    async def update_currency(self, community_id: uuid.UUID, currency: str) -> None:
        """@brief Set ``communities.currency`` (ISO 4217, validated by the caller)."""
        community = await self.get(community_id)
        if community is not None:
            community.currency = currency
            await self._session.flush()
