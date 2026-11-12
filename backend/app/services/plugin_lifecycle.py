"""@file plugin_lifecycle.py
@brief Two-phase plugin install/upgrade (request -> review -> confirm).

Staged data lives in ``Plugin.pending_manifest``. A staged new install is a
soft-deleted row (not installed) until confirmed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from packaging.version import Version

from app.core.exceptions import ConflictError, GoneError, NotFoundError, ValidationError
from app.core.i18n import _
from app.models.plugin import Plugin
from app.plugins.api_keys import generate_api_key
from app.plugins.manifest import PluginManifest, is_compatible
from app.services.plugin_service import PluginService

STAGE_TTL = timedelta(hours=1)


def permission_diff(requested: list[str], granted: list[str]) -> dict[str, list[str]]:
    """@brief Compare requested permissions with those previously granted."""
    return {
        "permissions_requested": sorted(requested),
        "permissions_previously_granted": sorted(granted),
        "new_permissions": sorted(set(requested) - set(granted)),
        "removed_permissions": sorted(set(granted) - set(requested)),
    }


def _perms(m: PluginManifest) -> list[str]:
    return [p.value for p in m.permissions]


class PluginLifecycleService(PluginService):
    """@brief Plugin service extended with the confirmation flows."""

    def _check_compat(self, m: PluginManifest) -> None:
        if not is_compatible(m, self._core):
            raise ValidationError(
                message=_("Plugin requires core version >= %(v)s") % {"v": m.min_core_version}
            )

    @staticmethod
    def _stage(kind: str, m: PluginManifest) -> dict[str, Any]:
        return {
            "kind": kind,
            "staged_at": datetime.now(UTC).isoformat(),
            "manifest": m.model_dump(mode="json"),
        }

    @staticmethod
    def _staged(row: Plugin | None, kind: str) -> dict[str, Any]:
        """@brief Return live staged data or raise (404 missing, 410 expired)."""
        pm = row.pending_manifest if row else None
        if row is None or not pm or pm.get("kind") != kind:
            raise NotFoundError(message=_("No pending request for this plugin"))
        if datetime.now(UTC) - datetime.fromisoformat(pm["staged_at"]) > STAGE_TTL:
            raise GoneError(message=_("Staged request expired; request again"))
        return pm

    def _review(self, m: PluginManifest, granted: list[str]) -> dict[str, Any]:
        return {
            "plugin_id": m.id,
            "manifest": m.model_dump(mode="json"),
            **permission_diff(_perms(m), granted),
        }

    async def request_install(self, plugin_id: str) -> dict[str, Any]:
        """@brief Validate and stage an install; nothing is enabled."""
        m = self.read_manifest(plugin_id)
        self._check_compat(m)
        if await self._repo.get(plugin_id, self._cid) is not None:
            raise ConflictError(message=_("Plugin already installed"))
        row = await self._repo.get(plugin_id, self._cid, include_deleted=True)
        if row is None:
            row = Plugin(id=plugin_id, community_id=self._cid)
            row.permissions_granted, row.settings = [], {}
        row.name, row.version = m.name, m.version
        row.is_enabled, row.deleted_at = False, datetime.now(UTC)
        row.pending_manifest = self._stage("install", m)
        await self._repo.save(row)
        return self._review(m, [])

    async def confirm_install(self, plugin_id: str) -> tuple[Plugin, str, list[str]]:
        """@brief Activate a staged install, issue the API key.
        @return (row, plaintext key, permissions granted).
        """
        row = await self._repo.get(plugin_id, self._cid, include_deleted=True)
        if row is not None and row.deleted_at is None:
            raise ConflictError(message=_("Plugin already installed"))
        pm = self._staged(row, "install")
        m = self.read_manifest(plugin_id)
        if m.model_dump(mode="json") != pm["manifest"]:
            raise ConflictError(message=_("Plugin changed since review; request again"))
        assert row is not None
        perms = _perms(m)
        row.permissions_granted, row.settings = perms, {}
        row.is_enabled, row.deleted_at, row.pending_manifest = True, None, None
        row.installed_at = datetime.now(UTC)
        row = await self._repo.save(row)
        plain, hashed = generate_api_key(plugin_id)
        await self._keys.create(
            plugin_id=plugin_id, community_id=self._cid, key_hash=hashed, key_hint=plain[-4:]
        )
        return row, plain, perms

    async def request_upgrade(self, plugin_id: str) -> dict[str, Any]:
        """@brief Stage an upgrade to the on-disk version and return the diff."""
        row = await self._installed(plugin_id)
        m = self.read_manifest(plugin_id)
        if Version(m.version) <= Version(row.version):
            raise ValidationError(message=_("New version must be greater than installed"))
        self._check_compat(m)
        row.pending_manifest = self._stage("upgrade", m)
        await self._repo.save(row)
        return {
            **self._review(m, list(row.permissions_granted)),
            "current_version": row.version,
            "new_version": m.version,
        }

    async def confirm_upgrade(self, plugin_id: str) -> tuple[Plugin, dict[str, Any]]:
        """@brief Apply a staged upgrade.

        @return Updated plugin row and the permission diff.
        """
        row = await self._installed(plugin_id)
        pm = self._staged(row, "upgrade")
        m = self.read_manifest(plugin_id)
        if m.model_dump(mode="json") != pm["manifest"]:
            raise ConflictError(message=_("Plugin changed since review; request again"))
        diff = permission_diff(_perms(m), list(row.permissions_granted))
        row.version, row.name = m.version, m.name
        row.permissions_granted = _perms(m)
        row.pending_manifest = None
        return await self._repo.save(row), diff
