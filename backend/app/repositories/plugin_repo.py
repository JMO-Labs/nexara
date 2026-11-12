"""@file plugin_repo.py
@brief Repository for installed plugins (community-scoped, soft-delete aware).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin import Plugin


class PluginRepository:
    """@brief Async access to ``plugins``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, plugin_id: str, community_id: uuid.UUID, include_deleted: bool = False
    ) -> Plugin | None:
        """@brief Fetch one plugin; soft-deleted rows only when requested."""
        stmt = select(Plugin).where(Plugin.id == plugin_id, Plugin.community_id == community_id)
        if not include_deleted:
            stmt = stmt.where(Plugin.deleted_at.is_(None))
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list(self, community_id: uuid.UUID) -> list[Plugin]:
        """@brief Installed (not soft-deleted) plugins ordered by id."""
        stmt = (
            select(Plugin)
            .where(Plugin.community_id == community_id, Plugin.deleted_at.is_(None))
            .order_by(Plugin.id)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def save(self, row: Plugin) -> Plugin:
        """@brief Add/flush a plugin row and refresh server-side fields."""
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row
