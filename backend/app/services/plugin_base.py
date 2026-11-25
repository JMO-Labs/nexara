"""
@file plugin_base.py
@brief Shared state and helpers for PluginService: audit, lookup, review, bot accounts,
       community activation/deactivation.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.encryption import derive_fernet_key, encrypt_secret
from app.core.exceptions import AppError, NotFoundError
from app.models.plugin import PluginCommunity, PluginInstall
from app.models.user import User
from app.plugins.manifest import PluginManifest, is_compatible
from app.plugins.tokens import new_token
from app.repositories.plugin_repo import PluginRepository
from app.repositories.user_repo import UserRepository
from app.schemas.plugin import PluginCredentials, PluginInstallOut
from app.services.plugin_host_client import HostPluginStatus


def specs(fields: dict[str, Any]) -> dict[str, Any]:
    """@return Field specs as plain dicts."""
    return {k: f.model_dump() for k, f in fields.items()}


class PluginServiceBase:
    """@brief Tenant-scoped (``community_id``) plugin state shared by the service mixins."""

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
        self._settings = settings
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

    async def _out(
        self, inst: PluginInstall, host: dict[str, HostPluginStatus] | None = None
    ) -> PluginInstallOut:
        m = self._manifest(inst)
        pc = await self._repo.get_community(inst.id, self._cid)
        row = (host or {}).get(inst.plugin_id)
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
            settings_schema=specs(m.settings),
            source="package" if inst.package_url else "url",
            host_status=row.status if row else None,
            host_error=row.last_error if row else None,
        )

    async def _review(self, m: PluginManifest, approved: list[str]) -> None:
        """@brief Compatibility, full scope approval and uniqueness checks before install."""
        if not is_compatible(m):
            raise AppError(
                code="plugin_incompatible", message="Plugin needs a newer Nexara", status_code=422
            )
        if set(approved) != set(m.scopes):
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
            # email is globally unique: include the community
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
        """@brief Disable in a community: revoke tokens, deactivate the bot (no host call)."""
        pc.enabled = False
        await self._repo.revoke_tokens(inst.id, pc.community_id)
        if pc.bot_user_id is not None:
            bot = await self._users.get_by_id(pc.bot_user_id, pc.community_id)
            if bot is not None:
                bot.is_active = False
        await self._repo.upsert_community(pc)

    async def _activate(
        self, inst: PluginInstall, pc: PluginCommunity, community_id: uuid.UUID, mint: bool
    ) -> PluginCredentials | None:
        """
        @brief Enable in a community with a bot and a new webhook secret.
        @param mint Issue a token and return credentials (url mode); package installs get
            their token from the host push instead.
        """
        bot = await self._ensure_bot(inst, self._manifest(inst), community_id, pc)
        secret = secrets.token_hex(32)
        pc.enabled = True
        pc.bot_user_id = bot.id
        pc.webhook_secret = encrypt_secret(secret, self._key)
        await self._repo.revoke_tokens(inst.id, community_id)
        await self._repo.upsert_community(pc)
        if not mint:
            return None
        token, token_hash = new_token()
        await self._repo.add_token(inst.id, community_id, token_hash)
        return PluginCredentials(token=token, webhook_secret=secret, community_id=community_id)
