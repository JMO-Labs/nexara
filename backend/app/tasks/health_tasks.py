"""
@file health_tasks.py
@brief Beat task: record the beat heartbeat and raise disk/email admin alerts.

``worker_down`` is not raised here (this task runs on a worker, which just wrote the
heartbeat); the API-side watchdog in ``services/worker_watch.py`` is its only source.

Routed to the ``maintenance`` queue; runs every 5 minutes.
"""

from __future__ import annotations

import asyncio
import time
import uuid

import structlog

from app.core.config import get_settings
from app.core.valkey import DB_BROKER, DB_CACHE, create_pool
from app.db.session import async_session_factory
from app.services import system_health
from app.services.admin_alerts import admin_alert
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _check_async() -> list[str]:
    settings = get_settings()
    cid = uuid.UUID(settings.COMMUNITY_ID)
    # Own clients: asyncio.run gives each run a fresh loop, so the shared pool is unusable.
    cache = create_pool(settings, DB_CACHE, max_connections=2)
    broker = create_pool(settings, DB_BROKER, max_connections=2)
    fired: list[str] = []
    try:
        now = str(time.time())
        try:
            await cache.set("beat:last_run", now)
            await cache.set(system_health.WORKER_HEARTBEAT_KEY, now)
        except Exception:
            logger.warning("health_check.heartbeat_unavailable")
        async with async_session_factory() as session:
            health = await system_health.collect(session, settings, cache, broker)
            pct = health.disk.used_pct
            if pct is not None and pct > system_health.DISK_ALERT_PCT:
                fired.append("disk_high")
                await admin_alert(session, cid, "disk_high", {}, cache)
            _, err = await system_health.smtp_state(session, cid)
            if err:
                fired.append("email_failing")
                await admin_alert(session, cid, "email_failing", {}, cache)
            await session.commit()
    finally:
        await cache.aclose()
        await broker.aclose()
    return fired


@celery_app.task(name="app.tasks.health_tasks.check", queue="maintenance")
def check() -> dict[str, list[str]]:
    """
    @brief Write ``beat:last_run`` and fire disk/email alerts (deduped downstream).

    @return Dict with the alert kinds raised this run.
    """
    return {"alerts": asyncio.run(_check_async())}
