"""
@file plugin_service.py
@brief Plugin install/enable/disable/uninstall, settings, user prefs and bot accounts.

Shared helpers live in ``plugin_base``; host-run (package) plugin operations in
``plugin_host_ops``.
"""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import urlparse

from app.core.exceptions import AppError, NotFoundError
from app.models.plugin import PluginCommunity, PluginInstall
from app.plugins.fetch import endpoint_allowed, fetch_manifest_text
from app.plugins.manifest import PluginManifest, parse_manifest, validate_values
from app.schemas.plugin import (
    PackageInstall,
    PluginCommunityOut,
    PluginCredentials,
    PluginInstallIn,
    PluginInstallOut,
    PluginUiOut,
    UrlInstall,
)
from app.services.plugin_base import specs
from app.services.plugin_host_ops import PluginHostOps
from app.services.plugin_settings import (
    decrypt_settings,
    mask_settings,
    merge_settings,
    prefs_with_defaults,
)


class PluginService(PluginHostOps):
    """@brief Business logic for plugins; tenant-scoped by ``community_id``."""

    # -- install / uninstall ------------------------------------------------

    async def install(self, body: PluginInstallIn) -> PluginInstallOut:
        """
        @brief Install from a manifest URL or a package after the admin approved every scope.
        @raises AppError ``not_supported`` (index), ``scopes_not_approved`` (with details),
            ``plugin_already_installed``, ``endpoint_insecure`` (http, unless dev/plugin host).
        Package installs are only verified and recorded; see ``_install_package``.
        """
        if isinstance(body, PackageInstall):
            return await self._install_package(body)
        if not isinstance(body, UrlInstall):
            raise AppError(
                code="not_supported", message="Install source not supported", status_code=422
            )
        if urlparse(body.endpoint_url).scheme not in ("http", "https"):
            raise AppError(
                code="invalid_endpoint_url", message="Endpoint must be http(s)", status_code=422
            )
        if not endpoint_allowed(body.endpoint_url):
            raise AppError(
                code="endpoint_insecure",
                message="Endpoint must be https (or the configured plugin host)",
                status_code=422,
            )
        m = parse_manifest(await fetch_manifest_text(body.manifest_url))
        await self._review(m, body.approved_scopes)
        inst = await self._repo.create_install(
            plugin_id=m.id,
            version=m.version,
            manifest=m.model_dump(mode="json"),
            manifest_url=body.manifest_url,
            endpoint_url=body.endpoint_url,
            granted_scopes=list(m.scopes),
            status="running",
        )
        await self._log("plugin.installed", m.id, {"version": m.version, "scopes": m.scopes})
        return await self._out(inst)

    async def uninstall(self, plugin_id: str, delete_content: bool = False) -> str | None:
        """
        @brief Disable everywhere (tokens revoked, bots inactive), optionally hide bot
            content, remove from the plugin host (best-effort) and delete the install.
        @return None, or the host error key: ``unreachable`` (install deleted; the poll
            removes it from the host later) or ``cleanup_failed`` (install kept, disabled;
            uninstall again to retry).
        """
        inst = await self._install(plugin_id)
        for pc in await self._repo.list_communities(inst.id):
            await self._deactivate(inst, pc)
            if delete_content and pc.bot_user_id is not None:
                await self._repo.soft_delete_bot_content(pc.bot_user_id)
        err = await self._host_delete(inst, purge=delete_content)
        if err == "cleanup_failed":
            inst.status = "disabled"
            await self._log("plugin.uninstall_incomplete", plugin_id, {"host_error": err})
            return err
        await self._repo.delete_install(inst.id)
        await self._log("plugin.uninstalled", plugin_id, {"delete_content": delete_content})
        return err

    # -- enable / disable ---------------------------------------------------

    async def set_community(
        self,
        plugin_id: str,
        community_id: uuid.UUID,
        enabled: bool | None = None,
        settings: dict[str, Any] | None = None,
    ) -> PluginCommunityOut:
        """
        @brief Enable/disable the plugin in a community and/or update its settings.

        Enabling from a disabled state (url mode) returns fresh credentials once.
        Package installs instead push their env to the plugin host on a real change:
        enable / settings fail with 503 if the host is down (rolled back); disable always
        commits (token revoked, bot inactive) and reports ``host_error`` if the host
        could not be told.
        """
        inst = await self._install(plugin_id)
        m = self._manifest(inst)
        pc = await self._repo.get_community(inst.id, community_id) or PluginCommunity(
            install_id=inst.id, community_id=community_id, enabled=False, settings={}
        )
        if settings is not None:
            pc.settings = merge_settings(m, dict(pc.settings or {}), settings, self._key)
            await self._repo.upsert_community(pc)
            await self._log("plugin.settings_updated", plugin_id, {"keys": sorted(settings)})
        creds: PluginCredentials | None = None
        flipped = False
        if enabled is True and not pc.enabled:
            creds = await self._activate(inst, pc, community_id, mint=not inst.package_url)
            flipped = True
            await self._log("plugin.enabled", plugin_id, {"community_id": str(community_id)})
        elif enabled is False and pc.enabled:
            await self._deactivate(inst, pc)
            flipped = True
            await self._log("plugin.disabled", plugin_id, {"community_id": str(community_id)})
        host_error = None
        if inst.package_url and (flipped or (settings is not None and pc.enabled)):
            host_error = await self._sync_host(inst, strict=bool(pc.enabled))
        return PluginCommunityOut(
            plugin_id=plugin_id,
            enabled=bool(pc.enabled),
            bot_user_id=pc.bot_user_id,
            settings=mask_settings(m, dict(pc.settings or {})),
            credentials=creds,
            host_error=host_error,
        )

    # -- settings / prefs ---------------------------------------------------

    async def get_settings(self, plugin_id: str) -> dict[str, Any]:
        """@brief Settings for this community; secrets masked as ``{"set": bool}``."""
        inst = await self._install(plugin_id)
        pc = await self._repo.get_community(inst.id, self._cid)
        return mask_settings(self._manifest(inst), dict(pc.settings or {}) if pc else {})

    async def update_settings(self, plugin_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """@brief Validate and store settings; blank secret keeps the old value."""
        out = await self.set_community(plugin_id, self._cid, settings=values)
        return out.settings

    def decrypted_settings(self, pc: PluginCommunity, manifest: PluginManifest) -> dict[str, Any]:
        """@brief Plaintext settings for the plugin host only."""
        return decrypt_settings(manifest, dict(pc.settings or {}), self._key)

    async def _enabled(self, plugin_id: str) -> tuple[PluginInstall, PluginManifest]:
        inst = await self._install(plugin_id)
        pc = await self._repo.get_community(inst.id, self._cid)
        if pc is None or not pc.enabled or inst.status != "running":
            raise NotFoundError(message="Plugin not found")
        return inst, self._manifest(inst)

    async def get_user_prefs(self, plugin_id: str, user_id: uuid.UUID) -> dict[str, Any]:
        """@brief A member's prefs with defaults (booleans default off)."""
        inst, m = await self._enabled(plugin_id)
        stored = await self._repo.get_user_pref(inst.id, user_id, self._cid)
        return prefs_with_defaults(m, stored)

    async def set_user_prefs(
        self, plugin_id: str, user_id: uuid.UUID, values: dict[str, Any]
    ) -> dict[str, Any]:
        """@brief Validate and merge a member's prefs."""
        inst, m = await self._enabled(plugin_id)
        validate_values(m.user_prefs, values)
        stored = await self._repo.get_user_pref(inst.id, user_id, self._cid)
        await self._repo.set_user_pref(inst.id, user_id, self._cid, {**stored, **values})
        return prefs_with_defaults(m, {**stored, **values})

    # -- listings -------------------------------------------------------------

    async def list_enabled_ui(self) -> list[PluginUiOut]:
        """@brief Member-facing prefs/composer flag specs of running plugins enabled here."""
        out: list[PluginUiOut] = []
        for inst in await self._repo.list_enabled_installs(self._cid):
            m = self._manifest(inst)
            out.append(
                PluginUiOut(
                    plugin_id=inst.plugin_id,
                    name=m.name,
                    user_prefs=specs(m.user_prefs),
                    composer_flags=specs(m.composer_flags),
                )
            )
        return out
