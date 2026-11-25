"""
@file plugin_host_tasks.py
@brief Beat task (every 60 s, ``maintenance``): sync plugin-host status into plugin_installs.

Installs enabled somewhere: host ``running`` → ``running``; ``failed``/``sandbox_unavailable``
→ ``failed`` plus one ``plugin_failed`` admin alert (on the transition only);
``needs_config``/``stopped`` or unknown to the host (e.g. after a host restart) → re-PUT
with fresh env.
Installs enabled nowhere (or blocked) but live on the host → stop. Host plugins with no
package install → delete (uninstalled while the host was down).
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.encryption import derive_fernet_key
from app.core.exceptions import AppError
from app.core.valkey import DB_CACHE, create_pool
from app.repositories.plugin_repo import PluginRepository
from app.services.admin_alerts import admin_alert
from app.services.plugin_host_client import HostPluginStatus, PluginHostClient
from app.services.plugin_host_sync import push_to_host
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)

FAILED = frozenset({"failed", "sandbox_unavailable"})
LIVE = frozenset({"running", "installing"})
# enabled but not running on the host (host restart, or stopped while Nexara was down)
REPUSH = frozenset({"needs_config", "stopped"})


async def _quiet(coro: Awaitable[None], event: str, plugin_id: str) -> None:
    try:
        await coro
    except AppError as e:
        logger.warning(event, plugin_id=plugin_id, code=e.code)


async def _sync_one(
    session: AsyncSession,
    repo: PluginRepository,
    client: PluginHostClient,
    redis: Redis | None,
    plugin_id: str,
    row: HostPluginStatus | None,
) -> None:
    settings = get_settings()
    inst = await repo.get_install(plugin_id)
    if inst is None:
        return
    enabled = inst.status != "blocked" and any(
        pc.enabled for pc in await repo.list_communities(inst.id)
    )
    if not enabled:  # Nexara disabled it (maybe while the host was down): stop it there
        if row is not None and row.status in LIVE:
            await _quiet(client.stop(plugin_id), "plugin_host_poll.stop_failed", plugin_id)
        return
    if row is None or row.status in REPUSH:
        try:
            await push_to_host(repo, inst, derive_fernet_key(settings.SECRET_KEY), settings, client)
        except AppError:
            logger.warning("plugin_host_poll.repush_failed", plugin_id=plugin_id)
            await session.rollback()
            return
    elif row.status == "running":
        inst.status = "running"
    elif row.status in FAILED and inst.status != "failed":
        inst.status = "failed"
        await admin_alert(
            session,
            uuid.UUID(settings.COMMUNITY_ID),
            "plugin_failed",
            {"key": plugin_id, "plugin_id": plugin_id, "reason": row.last_error or row.status},
            redis,
        )
    await session.commit()


async def sync_installs(
    session: AsyncSession, client: PluginHostClient, redis: Redis | None = None
) -> None:
    """
    @brief One poll pass: reconcile every package install, then remove host plugins that
        Nexara no longer has (uninstalled while the host was down). Commits per install.
    @param redis Cache client for admin-alert dedupe (own pool under ``asyncio.run``).
    """
    try:
        rows = {r.id: r for r in await client.status()}
    except AppError:
        logger.warning("plugin_host_poll.unreachable")
        return
    repo = PluginRepository(session)
    ids = [i.plugin_id for i in await repo.list_installs() if i.package_url]
    for plugin_id in ids:  # re-read each: a rollback expires loaded rows
        await _sync_one(session, repo, client, redis, plugin_id, rows.get(plugin_id))
    known = set(ids)
    for plugin_id, row in rows.items():
        # "installing" may be an install whose transaction has not committed yet
        if plugin_id not in known and row.status != "installing":
            await _quiet(
                client.delete(plugin_id, purge=False), "plugin_host_poll.delete_failed", plugin_id
            )


async def _poll_async() -> None:
    from app.db.session import async_session_factory

    settings = get_settings()
    if not settings.PLUGIN_HOST_URL:
        return
    client = PluginHostClient.from_settings(settings)
    cache = create_pool(settings, DB_CACHE, max_connections=2)
    try:
        async with async_session_factory() as session:
            await sync_installs(session, client, cache)
    finally:
        await cache.aclose()


@celery_app.task(name="app.tasks.plugin_host_tasks.poll", queue="maintenance")
def poll() -> None:
    """@brief Celery entry point for the 60 s plugin-host status sync."""
    asyncio.run(_poll_async())
