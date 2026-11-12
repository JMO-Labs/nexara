"""@file plugin_service.py
@brief Plugin registry service: install, lifecycle and settings.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packaging.version import Version
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.i18n import _
from app.models.plugin import Plugin
from app.plugins.api_keys import generate_api_key
from app.plugins.manifest import PluginManifest, is_compatible, load_manifest
from app.plugins.utils import validate_plugin_dir
from app.repositories.plugin_key_repo import PluginApiKeyRepository
from app.repositories.plugin_repo import PluginRepository

SECRET_MASK = "********"
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "boolean": (bool,),
    "number": (int, float),
}


class PluginService:
    """@brief Business rules for the plugin registry of one community."""

    def __init__(
        self,
        repo: PluginRepository,
        key_repo: PluginApiKeyRepository,
        community_id: uuid.UUID,
        plugins_dir: Path,
        core_version: str,
    ) -> None:
        self._repo = repo
        self._keys = key_repo
        self._cid = community_id
        self._dir = plugins_dir
        self._core = core_version

    def read_manifest(self, plugin_id: str) -> PluginManifest:
        """
        @brief Load and validate a plugin manifest from the plugins directory.
        @throws NotFoundError if the id is malformed or the directory/manifest is missing.
        @throws ValidationError if the manifest is invalid or id mismatches.
        """
        pdir = self._dir / plugin_id
        if not _ID_RE.match(plugin_id) or not pdir.is_dir():
            raise NotFoundError(message=_("Plugin not found"))
        try:
            manifest = load_manifest(pdir)
        except FileNotFoundError:
            raise NotFoundError(message=_("Plugin not found")) from None
        except (PydanticValidationError, ValueError) as exc:
            raise ValidationError(
                message=_("Invalid plugin manifest"), details={"error": str(exc)}
            ) from exc
        if manifest.id != plugin_id:
            raise ValidationError(message=_("Manifest id does not match directory"))
        return manifest

    async def _installed(self, plugin_id: str) -> Plugin:
        row = await self._repo.get(plugin_id, self._cid)
        if row is None:
            raise NotFoundError(message=_("Plugin not found"))
        return row

    async def list(self) -> list[Plugin]:
        """@brief Installed plugins of the community."""
        return await self._repo.list(self._cid)

    async def install(self, plugin_id: str) -> tuple[Plugin, str]:
        """
        @brief Install from the plugins dir and issue an API key.
        @return (plugin row, plaintext API key shown once).
        @throws ConflictError if already installed.
        """
        manifest = self.read_manifest(plugin_id)
        if not is_compatible(manifest, self._core):
            raise ValidationError(
                message=_("Plugin requires core version >= %(v)s")
                % {"v": manifest.min_core_version}
            )
        if await self._repo.get(plugin_id, self._cid) is not None:
            raise ConflictError(message=_("Plugin already installed"))
        perms = [p.value for p in manifest.permissions]
        row = await self._repo.get(plugin_id, self._cid, include_deleted=True)
        if row is None:
            row = Plugin(id=plugin_id, community_id=self._cid)
        row.name, row.version = manifest.name, manifest.version
        row.permissions_granted, row.settings = perms, {}
        row.is_enabled, row.deleted_at = False, None
        row = await self._repo.save(row)
        plain, hashed = generate_api_key(plugin_id)
        await self._keys.create(
            plugin_id=plugin_id, community_id=self._cid, key_hash=hashed, key_hint=plain[-4:]
        )
        return row, plain

    async def uninstall(self, plugin_id: str) -> Plugin:
        """@brief Soft-delete the plugin, disable it and revoke its keys."""
        row = await self._installed(plugin_id)
        row.deleted_at, row.is_enabled = datetime.now(UTC), False
        await self._keys.revoke_all(plugin_id, self._cid)
        return await self._repo.save(row)

    async def set_enabled(self, plugin_id: str, enabled: bool) -> Plugin:
        """@brief Enable or disable an installed plugin."""
        row = await self._installed(plugin_id)
        row.is_enabled = enabled
        return await self._repo.save(row)

    def _specs(self, plugin_id: str) -> dict[str, Any]:
        try:
            return dict(self.read_manifest(plugin_id).settings)
        except NotFoundError:
            return {}

    async def get_settings(self, plugin_id: str) -> dict[str, Any]:
        """@brief Settings with secret values masked."""
        row = await self._installed(plugin_id)
        specs = self._specs(plugin_id)
        return {
            k: (SECRET_MASK if k in specs and specs[k].secret and v else v)
            for k, v in row.settings.items()
        }

    async def update_settings(self, plugin_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """
        @brief Merge validated key-values into the plugin settings.
        @throws ValidationError for keys not declared in the manifest or wrong types.
        """
        row = await self._installed(plugin_id)
        specs = self._specs(plugin_id)
        for key, val in values.items():
            spec = specs.get(key)
            if spec is None:
                raise ValidationError(message=_("Unknown setting: %(k)s") % {"k": key})
            ok = isinstance(val, _TYPES[spec.type]) and not (
                spec.type != "boolean" and isinstance(val, bool)
            )
            if not ok:
                raise ValidationError(message=_("Invalid type for setting: %(k)s") % {"k": key})
        row.settings = {**row.settings, **values}
        await self._repo.save(row)
        return await self.get_settings(plugin_id)

    async def upgrade(self, plugin_id: str, new_version: str) -> Plugin:
        """
        @brief Upgrade an installed plugin to the version found on disk.
        @param new_version Expected target version; must equal the manifest version.
        @throws NotFoundError if not installed.
        @throws ValidationError on version mismatch, non-increase or core incompatibility.
        """
        row = await self._installed(plugin_id)
        manifest = validate_plugin_dir(self._dir / plugin_id)
        if manifest.id != plugin_id or manifest.version != new_version:
            raise ValidationError(message=_("Plugin on disk does not match requested version"))
        if Version(new_version) <= Version(row.version):
            raise ValidationError(message=_("New version must be greater than installed"))
        if not is_compatible(manifest, self._core):
            raise ValidationError(
                message=_("Plugin requires core version >= %(v)s")
                % {"v": manifest.min_core_version}
            )
        row.version = manifest.version
        row.permissions_granted = [p.value for p in manifest.permissions]
        return await self._repo.save(row)
