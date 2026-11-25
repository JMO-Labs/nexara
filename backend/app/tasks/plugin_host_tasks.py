"""
@file plugin_host_tasks.py
@brief Beat task (every 60 s, ``maintenance``): sync plugin-host status into plugin_installs.

host ``running`` → install ``running``; ``failed``/``sandbox_unavailable`` → install
``failed`` plus one ``plugin_failed`` admin alert (on the transition only); ``needs_config``
or unknown to the host (e.g. after a host restart) → re-PUT with fresh env.
"""

from __future__ import annotations

import asyncio
import uuid

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.encryption import derive_fernet_key
from app.core.exceptions import AppError
from app.core.valkey import DB_CACHE, create_pool
from app.repositories.plugin_repo import PluginRepository
from app.services.admin_alerts import admin_alert
from app.services.plugin_host_client import PluginHostClient
from app.services.plugin_host_sync import push_to_host
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)

FAILED = frozenset({"failed", "sandbox_unavailable"})
SKIP = frozenset({"disabled", "blocked"})


async def sync_installs(
    session: AsyncSession, client: PluginHostClient, redis: Redis | None = None
) -> None:
    """
    @brief One poll pass over package installs (commits on the caller's session).
    @param redis Cache client for admin-alert dedupe (own pool under ``asyncio.run``).
    """
    settings = get_settings()
    key = derive_fernet_key(settings.SECRET_KEY)
    cid = uuid.UUID(settings.COMMUNITY_ID)
    try:
        rows = {r.id: r for r in await client.status()}
    except AppError:
        logger.warning("plugin_host_poll.unreachable")
        return
    repo = PluginRepository(session)
    ids = [i.plugin_id for i in await repo.list_installs() if i.package_url]
    for plugin_id in ids:  # re-read each: a rollback below expires loaded rows
        inst = await repo.get_install(plugin_id)
        if inst is None or inst.status in SKIP:
            continue
        row = rows.get(inst.plugin_id)
        if row is None or row.status == "needs_config":
            try:
                await push_to_host(repo, inst, key, settings, client)
            except AppError:
                logger.warning("plugin_host_poll.repush_failed", plugin_id=plugin_id)
                await session.rollback()
                continue
        elif row.status == "running":
            inst.status = "running"
        elif row.status in FAILED and inst.status != "failed":
            inst.status = "failed"
            reason = row.last_error or row.status
            await admin_alert(
                session,
                cid,
                "plugin_failed",
                {"key": inst.plugin_id, "plugin_id": inst.plugin_id, "reason": reason},
                redis,
            )
        await session.commit()


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
