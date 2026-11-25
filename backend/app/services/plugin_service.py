"""
@file plugin_service.py
@brief Plugin install/enable/disable/uninstall, settings, user prefs and bot accounts.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.encryption import derive_fernet_key, encrypt_secret
from app.core.exceptions import AppError, NotFoundError
from app.models.plugin import PluginCommunity, PluginInstall
from app.models.user import User
from app.plugins.fetch import endpoint_allowed, fetch_manifest_text
from app.plugins.manifest import PluginManifest, is_compatible, parse_manifest, validate_values
from app.plugins.tokens import new_token
from app.repositories.plugin_repo import PluginRepository
from app.repositories.user_repo import UserRepository
from app.schemas.plugin import (
    PluginCommunityOut,
    PluginCredentials,
    PluginInstallIn,
    PluginInstallOut,
    PluginUiOut,
    UrlInstall,
)
from app.services.plugin_settings import (
    decrypt_settings,
    mask_settings,
    merge_settings,
    prefs_with_defaults,
)


def _specs(fields: dict[str, Any]) -> dict[str, Any]:
    return {k: f.model_dump() for k, f in fields.items()}


class PluginService:
    """@brief Business logic for plugins; tenant-scoped by ``community_id``."""

    def __init__(
        self,
        repo: PluginRepository,
        user_repo: UserRepository,
        community_id: uuid.UUID,
        session: AsyncSession,
        settings: Settings,
        audit_repo: Any | None = None,
        actor_id: uuid.UUID | None = None,
        ip_address: str | None = None,
    ) -> None:
        self._repo = repo
        self._users = user_repo
        self._cid = community_id
        self._session = session
        self._key = derive_fernet_key(settings.SECRET_KEY)
        self._audit = audit_repo
        self._actor = actor_id
        self._ip = ip_address

    async def _log(self, action: str, plugin_id: str, extra: dict[str, Any] | None = None) -> None:
        if self._audit is not None:
            await self._audit.append(
                actor_id=self._actor,
                action=action,
                target_type="plugin",
                extra_data={"plugin_id": plugin_id, **(extra or {})},
                ip_address=self._ip,
            )

    async def _install(self, plugin_id: str) -> PluginInstall:
        inst = await self._repo.get_install(plugin_id)
        if inst is None:
            raise NotFoundError(message="Plugin not found")
        return inst

    @staticmethod
    def _manifest(inst: PluginInstall) -> PluginManifest:
        return PluginManifest.model_validate(inst.manifest)

    async def _out(self, inst: PluginInstall) -> PluginInstallOut:
        m = self._manifest(inst)
        pc = await self._repo.get_community(inst.id, self._cid)
        return PluginInstallOut(
            id=inst.id,
            plugin_id=inst.plugin_id,
            name=m.name,
            version=inst.version,
            status=inst.status,
            tier=inst.tier,
            scopes=list(inst.granted_scopes),
            events=m.events,
            egress=m.egress,
            enabled=bool(pc and pc.enabled),
            bot_user_id=pc.bot_user_id if pc else None,
            settings_schema=_specs(m.settings),
        )

    # -- install / uninstall ------------------------------------------------

    async def install(self, body: PluginInstallIn) -> PluginInstallOut:
        """
        @brief Install from a manifest URL after the admin approved every scope.
        @raises AppError ``not_supported`` (422) for package/index sources,
            ``scopes_not_approved`` (422) with the review details, ``plugin_already_installed``,
            ``endpoint_insecure`` (422) for http unless dev flag or PLUGIN_HOST_URL origin.
        """
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
        if not is_compatible(m):
            raise AppError(
                code="plugin_incompatible", message="Plugin needs a newer Nexara", status_code=422
            )
        if set(body.approved_scopes) != set(m.scopes):
            raise AppError(
                code="scopes_not_approved",
                message="All requested scopes must be approved",
                status_code=422,
                details={"scopes": m.scopes, "events": m.events, "egress": m.egress},
            )
        if await self._repo.get_install(m.id) is not None:
            raise AppError(
                code="plugin_already_installed", message="Plugin already installed", status_code=409
            )
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

    async def uninstall(self, plugin_id: str, delete_content: bool = False) -> None:
        """@brief Disable everywhere, optionally hide bot content, delete the install."""
        inst = await self._install(plugin_id)
        for pc in await self._repo.list_communities(inst.id):
            await self._deactivate(inst, pc)
            if delete_content and pc.bot_user_id is not None:
                await self._repo.soft_delete_bot_content(pc.bot_user_id)
        await self._repo.delete_install(inst.id)
        await self._log("plugin.uninstalled", plugin_id, {"delete_content": delete_content})

    # -- enable / disable ---------------------------------------------------

    async def _unique_username(self, base: str) -> str:
        cand, n = base, 1
        while await self._users.username_exists(cand):
            cand = f"{base}-bot" if n == 1 else f"{base}-bot{n}"
            n += 1
        return cand

    async def _ensure_bot(
        self, inst: PluginInstall, m: PluginManifest, community_id: uuid.UUID, pc: PluginCommunity
    ) -> User:
        if pc.bot_user_id is not None:
            bot = await self._users.get_by_id(pc.bot_user_id, community_id)
            if bot is not None:
                bot.is_active = True
                return bot
        bot = User(
            community_id=community_id,
            email=f"{m.bot_username}+{inst.id}.{community_id.hex}@plugins.invalid",
            username=await self._unique_username(m.bot_username),
            display_name=m.bot_display_name,
            password_hash=None,
            role="member",
            is_bot=True,
            is_active=True,
            onboarding_done_at=datetime.now(UTC),
        )
        created = await self._users.try_create(bot)
        if created is None:
            raise AppError(
                code="bot_conflict", message="Could not create bot account", status_code=409
            )
        return created

    async def _deactivate(self, inst: PluginInstall, pc: PluginCommunity) -> None:
        pc.enabled = False
        await self._repo.revoke_tokens(inst.id, pc.community_id)
        if pc.bot_user_id is not None:
            bot = await self._users.get_by_id(pc.bot_user_id, pc.community_id)
            if bot is not None:
                bot.is_active = False
        await self._repo.upsert_community(pc)

    async def _enable(
        self, inst: PluginInstall, pc: PluginCommunity, community_id: uuid.UUID
    ) -> PluginCredentials:
        bot = await self._ensure_bot(inst, self._manifest(inst), community_id, pc)
        token, token_hash = new_token()
        secret = secrets.token_hex(32)
        pc.enabled = True
        pc.bot_user_id = bot.id
        pc.webhook_secret = encrypt_secret(secret, self._key)
        await self._repo.revoke_tokens(inst.id, community_id)
        await self._repo.upsert_community(pc)
        await self._repo.add_token(inst.id, community_id, token_hash)
        return PluginCredentials(token=token, webhook_secret=secret, community_id=community_id)

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
        if enabled is True and not pc.enabled:
            creds = await self._enable(inst, pc, community_id)
            await self._log("plugin.enabled", plugin_id, {"community_id": str(community_id)})
        elif enabled is False and pc.enabled:
            await self._deactivate(inst, pc)
            await self._log("plugin.disabled", plugin_id, {"community_id": str(community_id)})
        return PluginCommunityOut(
            plugin_id=plugin_id,
            enabled=bool(pc.enabled),
            bot_user_id=pc.bot_user_id,
            settings=mask_settings(m, dict(pc.settings or {})),
            credentials=creds,
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

    async def list_installed(self) -> list[PluginInstallOut]:
        """@brief All installs with this community's enablement."""
        return [await self._out(i) for i in await self._repo.list_installs()]

    async def list_enabled_ui(self) -> list[PluginUiOut]:
        """@brief Member-facing prefs/composer flag specs of running plugins enabled here."""
        out: list[PluginUiOut] = []
        for inst in await self._repo.list_enabled_installs(self._cid):
            m = self._manifest(inst)
            out.append(
                PluginUiOut(
                    plugin_id=inst.plugin_id,
                    name=m.name,
                    user_prefs=_specs(m.user_prefs),
                    composer_flags=_specs(m.composer_flags),
                )
            )
        return out
