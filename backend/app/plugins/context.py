"""@file context.py
@brief PluginContext: permission-checked, community-scoped resource access.
"""

import time
import uuid
from collections import deque
from collections.abc import Callable, Iterator, MutableMapping
from typing import Any

import httpx
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin import PluginData
from app.plugins.manifest import PluginManifest, PluginPermission

NOTIFY_LIMIT_PER_MINUTE = 100


def _require(plugin_id: str, manifest: PluginManifest, perm: PluginPermission) -> None:
    """@brief Raise PermissionError unless manifest grants perm."""
    if perm not in manifest.permissions:
        raise PermissionError(f"Plugin '{plugin_id}' does not have permission '{perm.value}'")


class _Scoped:
    """@brief Base for proxies holding plugin identity and manifest."""

    def __init__(self, plugin_id: str, manifest: PluginManifest) -> None:
        self._plugin_id = plugin_id
        self._manifest = manifest

    def _need(self, perm: PluginPermission) -> None:
        _require(self._plugin_id, self._manifest, perm)


class PluginDB(_Scoped):
    """@brief Key-value access limited to the plugin_data table rows of one plugin/community."""

    def __init__(
        self, plugin_id: str, manifest: PluginManifest, session: AsyncSession, community_id: uuid.UUID
    ) -> None:
        super().__init__(plugin_id, manifest)
        self._session = session
        self._community_id = community_id

    def _scope(self) -> tuple[Any, Any]:
        return (PluginData.plugin_id == self._plugin_id, PluginData.community_id == self._community_id)

    async def get(self, key: str) -> Any:
        """@brief Read a value. @return Stored JSON or None."""
        self._need(PluginPermission.DB_READ)
        stmt = select(PluginData.value_json).where(*self._scope(), PluginData.key == key)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def set(self, key: str, value: Any) -> None:
        """@brief Upsert a value."""
        self._need(PluginPermission.DB_WRITE)
        stmt = insert(PluginData).values(
            plugin_id=self._plugin_id, community_id=self._community_id, key=key, value_json=value
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_plugin_data_key", set_={"value_json": stmt.excluded.value_json}
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def delete(self, key: str) -> None:
        """@brief Delete a key."""
        self._need(PluginPermission.DB_WRITE)
        await self._session.execute(delete(PluginData).where(*self._scope(), PluginData.key == key))
        await self._session.flush()


class PluginSettings(MutableMapping[str, Any]):
    """@brief Dict-like settings limited to keys declared in the manifest."""

    def __init__(self, manifest: PluginManifest, saved: dict[str, Any] | None) -> None:
        self._declared = set(manifest.settings)
        self._values = {k: v for k, v in (saved or {}).items() if k in self._declared}

    def __getitem__(self, key: str) -> Any:
        return self._values[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if key not in self._declared:
            raise KeyError(f"Setting '{key}' is not declared in the manifest")
        self._values[key] = value

    def __delitem__(self, key: str) -> None:
        del self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def set(self, key: str, value: Any) -> None:
        """@brief Set a declared setting (in memory; caller persists)."""
        self[key] = value


class PluginStorage(_Scoped):
    """@brief Storage proxy confined to ``plugins/{plugin_id}/``."""

    def __init__(self, plugin_id: str, manifest: PluginManifest, client: Any) -> None:
        super().__init__(plugin_id, manifest)
        self._client = client

    def _key(self, key: str) -> str:
        self._need(PluginPermission.STORAGE_ACCESS)
        parts = key.split("/")
        if not key or key.startswith("/") or any(p in ("", "..", ".") for p in parts):
            raise ValueError(f"Invalid storage key '{key}'")
        return f"plugins/{self._plugin_id}/{key}"

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        """@brief Store bytes."""
        await self._client.put(self._key(key), data, content_type)

    async def get(self, key: str) -> bytes:
        """@brief Fetch bytes."""
        return bytes(await self._client.get(self._key(key)))

    async def delete(self, key: str) -> None:
        """@brief Delete an object."""
        await self._client.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        """@brief Check existence."""
        return bool(await self._client.exists(self._key(key)))


class PluginContext:
    """@brief Scoped API object handed to plugins; immutable after creation."""

    __slots__ = (
        "_clock", "_notifications", "_sent", "_session", "_storage",
        "community_id", "db", "manifest", "plugin_id", "settings", "storage",
    )  # fmt: skip

    def __init__(
        self,
        plugin_id: str,
        manifest: PluginManifest,
        session: AsyncSession,
        community_id: uuid.UUID,
        storage_client: Any,
        notification_service: Any,
        settings: dict[str, Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """@param settings Saved config (Plugin.settings) merged over manifest declarations."""
        set_ = object.__setattr__
        set_(self, "plugin_id", plugin_id)
        set_(self, "manifest", manifest)
        set_(self, "community_id", community_id)
        set_(self, "_session", session)
        set_(self, "_storage", storage_client)
        set_(self, "_notifications", notification_service)
        set_(self, "_clock", clock or time.monotonic)
        set_(self, "_sent", deque())
        set_(self, "db", PluginDB(plugin_id, manifest, session, community_id))
        set_(self, "settings", PluginSettings(manifest, settings))
        set_(self, "storage", PluginStorage(plugin_id, manifest, storage_client))

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("PluginContext is immutable")

    async def notify(
        self,
        user_id: uuid.UUID,
        notification_type: str,
        payload: dict[str, Any] | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> Any:
        """@brief Send a notification (max 100/min per context).
        @throws PermissionError without send_notifications; RuntimeError when rate limited.
        """
        _require(self.plugin_id, self.manifest, PluginPermission.SEND_NOTIFICATIONS)
        now = self._clock()
        while self._sent and now - self._sent[0] >= 60:
            self._sent.popleft()
        if len(self._sent) >= NOTIFY_LIMIT_PER_MINUTE:
            raise RuntimeError(f"Plugin '{self.plugin_id}' notification rate limit exceeded")
        self._sent.append(now)
        return await self._notifications.notify(
            user_id, notification_type, payload or {}, actor_id=actor_id
        )

    def http_client(self) -> httpx.AsyncClient:
        """@brief Outbound HTTP client. @throws PermissionError without external_http."""
        _require(self.plugin_id, self.manifest, PluginPermission.EXTERNAL_HTTP)
        return httpx.AsyncClient(timeout=10.0)
