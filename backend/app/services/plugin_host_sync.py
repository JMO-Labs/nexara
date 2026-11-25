"""
@file plugin_host_sync.py
@brief Build a package plugin's env from its enabled communities and push it to the host.

Every push issues a fresh token per enabled community (previous ones revoked). The env
(tokens, webhook secrets, decrypted settings) goes only into the PUT body.
"""

from __future__ import annotations

import secrets
from typing import Any

from app.core.config import Settings
from app.core.encryption import decrypt_secret, encrypt_secret
from app.models.plugin import PluginInstall
from app.plugins.manifest import PluginManifest
from app.plugins.tokens import new_token
from app.repositories.plugin_repo import PluginRepository
from app.services.plugin_host_client import PluginHostClient
from app.services.plugin_settings import decrypt_settings


def endpoint_for(settings: Settings, plugin_id: str) -> str:
    """@return Delivery URL the host proxies to the plugin process."""
    return f"{settings.PLUGIN_HOST_URL.rstrip('/')}/plugins/{plugin_id}/events"


async def _communities(
    repo: PluginRepository, inst: PluginInstall, m: PluginManifest, key: bytes
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for pc in await repo.list_communities(inst.id):
        if not pc.enabled:
            continue
        if pc.webhook_secret:
            secret = decrypt_secret(pc.webhook_secret, key)
        else:
            secret = secrets.token_hex(32)
            pc.webhook_secret = encrypt_secret(secret, key)
            await repo.upsert_community(pc)
        token, token_hash = new_token()
        await repo.revoke_tokens(inst.id, pc.community_id)
        await repo.add_token(inst.id, pc.community_id, token_hash)
        out.append(
            {
                "community_id": str(pc.community_id),
                "token": token,
                "webhook_secret": secret,
                "settings": decrypt_settings(m, dict(pc.settings or {}), key),
                "bot_user_id": str(pc.bot_user_id) if pc.bot_user_id else None,
            }
        )
    return out


async def push_to_host(
    repo: PluginRepository,
    inst: PluginInstall,
    key: bytes,
    settings: Settings,
    client: PluginHostClient | None = None,
) -> None:
    """
    @brief PUT the install with fresh env, or stop it when no community has it enabled.

    Sets ``inst.status``: ``disabled`` when stopped, else ``installing`` unless it was
    already ``running`` (the host restarts it in place; the poll confirms).
    @raises AppError ``plugin_host_unavailable`` (503) / ``plugin_host_not_configured``.
    """
    client = client or PluginHostClient.from_settings(settings)
    await repo.lock_install(inst.id)  # one rotation at a time: never two active tokens
    m = PluginManifest.model_validate(inst.manifest)
    comms = await _communities(repo, inst, m, key)
    if not comms:
        inst.status = "disabled"
        await client.stop(inst.plugin_id)
        return
    default = next((c for c in comms if c["community_id"] == settings.COMMUNITY_ID), comms[0])
    body = {
        "version": inst.version,
        "package_url": inst.package_url,
        "sha256": inst.sha256,
        "runtime": m.runtime,
        "entrypoint": m.entrypoint,
        "env": {
            "NEXARA_TOKEN": default["token"],
            "NEXARA_WEBHOOK_SECRET": default["webhook_secret"],
            "NEXARA_SETTINGS": default["settings"],
            "NEXARA_COMMUNITIES": comms,
        },
    }
    await client.put(inst.plugin_id, body)
    if inst.status != "running":
        inst.status = "installing"
