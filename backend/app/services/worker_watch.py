"""
@file worker_watch.py
@brief API-side watchdog: alert admins when the worker heartbeat goes stale.

The health task runs inside a worker, so it cannot report that all workers are
dead. The API process polls ``health:worker_heartbeat`` instead.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import timedelta

import structlog

from app.core.config import get_settings
from app.core.valkey import DB_CACHE, get_pool
from app.db.session import async_session_factory
from app.services import system_health
from app.services.admin_alerts import admin_alert

logger = structlog.get_logger(__name__)

FIRST_DELAY = 120.0
INTERVAL = 300.0


def heartbeat_stale(raw: str | bytes | None, watching_for: timedelta) -> bool:
    """
    @brief True when the heartbeat is older than 12 min.

    A missing heartbeat only counts once we have watched for longer than the limit
    (fresh installs have not had a task run yet).
    """
    age = system_health.heartbeat_age(raw)
    if age is None:
        return watching_for > system_health.HEARTBEAT_STALE
    return age > system_health.HEARTBEAT_STALE


async def tick(started: float) -> bool:
    """@brief One check; alerts ``worker_down`` when stale. Returns True if alerted."""
    settings = get_settings()
    try:
        raw = await get_pool(settings, DB_CACHE).get(system_health.WORKER_HEARTBEAT_KEY)
    except Exception:
        return False  # Valkey down: not evidence about workers
    if not heartbeat_stale(raw, timedelta(seconds=time.monotonic() - started)):
        return False
    async with async_session_factory() as session:
        await admin_alert(session, uuid.UUID(settings.COMMUNITY_ID), "worker_down", {})
        await session.commit()
    return True


async def run_loop() -> None:
    """@brief Background loop for the API lifespan: first tick after 2 min, then every 5."""
    started = time.monotonic()
    await asyncio.sleep(FIRST_DELAY)
    while True:
        try:
            await tick(started)
        except Exception:
            logger.warning("worker_watch.tick_failed", exc_info=True)
        await asyncio.sleep(INTERVAL)
