"""@file plugin_key_repo.py
@brief Repository for plugin API keys (community-scoped).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin import Plugin, PluginApiKey


class PluginApiKeyRepository:
    """@brief Async access to ``plugin_api_keys``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def plugin_exists(self, plugin_id: str, community_id: uuid.UUID) -> bool:
        """@brief True if the plugin is installed (not soft-deleted)."""
        stmt = select(Plugin.id).where(
            Plugin.id == plugin_id,
            Plugin.community_id == community_id,
            Plugin.deleted_at.is_(None),
        )
        return (await self._session.execute(stmt)).first() is not None

    async def create(
        self, *, plugin_id: str, community_id: uuid.UUID, key_hash: str, key_hint: str
    ) -> PluginApiKey:
        """@brief Persist a new key hash."""
        row = PluginApiKey(
            plugin_id=plugin_id, community_id=community_id, key_hash=key_hash, key_hint=key_hint
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def list_for_plugin(self, plugin_id: str, community_id: uuid.UUID) -> list[PluginApiKey]:
        """@brief All keys (including revoked) for a plugin, newest first."""
        stmt = (
            select(PluginApiKey)
            .where(PluginApiKey.plugin_id == plugin_id, PluginApiKey.community_id == community_id)
            .order_by(PluginApiKey.created_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def active_keys_for_plugin(
        self, plugin_id: str, community_id: uuid.UUID
    ) -> list[PluginApiKey]:
        """@brief Non-revoked keys of an installed, enabled plugin in the community."""
        stmt = (
            select(PluginApiKey)
            .join(
                Plugin,
                (Plugin.id == PluginApiKey.plugin_id)
                & (Plugin.community_id == PluginApiKey.community_id),
            )
            .where(
                PluginApiKey.plugin_id == plugin_id,
                PluginApiKey.community_id == community_id,
                PluginApiKey.revoked_at.is_(None),
                Plugin.deleted_at.is_(None),
                Plugin.is_enabled.is_(True),
            )
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get(
        self, key_id: uuid.UUID, plugin_id: str, community_id: uuid.UUID
    ) -> PluginApiKey | None:
        """@brief Fetch one key scoped to plugin and community."""
        stmt = select(PluginApiKey).where(
            PluginApiKey.id == key_id,
            PluginApiKey.plugin_id == plugin_id,
            PluginApiKey.community_id == community_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def revoke(self, key: PluginApiKey) -> PluginApiKey:
        """@brief Mark a key revoked (idempotent)."""
        if key.revoked_at is None:
            key.revoked_at = datetime.now(UTC)
            await self._session.flush()
        return key

    async def revoke_all(self, plugin_id: str, community_id: uuid.UUID) -> None:
        """@brief Revoke every active key of a plugin."""
        for key in await self.active_keys_for_plugin_any(plugin_id, community_id):
            await self.revoke(key)

    async def active_keys_for_plugin_any(
        self, plugin_id: str, community_id: uuid.UUID
    ) -> list[PluginApiKey]:
        """@brief Non-revoked keys regardless of plugin enablement."""
        stmt = select(PluginApiKey).where(
            PluginApiKey.plugin_id == plugin_id,
            PluginApiKey.community_id == community_id,
            PluginApiKey.revoked_at.is_(None),
        )
        return list((await self._session.execute(stmt)).scalars().all())
