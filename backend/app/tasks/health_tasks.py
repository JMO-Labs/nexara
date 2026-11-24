"""
@file health_tasks.py
@brief Beat task: record the beat heartbeat and raise admin alerts for unhealthy state.

Routed to the ``maintenance`` queue; runs every 5 minutes.
"""

from __future__ import annotations

import asyncio
import time
import uuid

import structlog

from app.core.config import get_settings
from app.core.valkey import DB_CACHE, get_pool
from app.db.session import async_session_factory
from app.services import system_health
from app.services.admin_alerts import admin_alert
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _check_async() -> list[str]:
    settings = get_settings()
    cid = uuid.UUID(settings.COMMUNITY_ID)
    try:
        await get_pool(settings, DB_CACHE).set("beat:last_run", str(time.time()))
    except Exception:
        logger.warning("health_check.heartbeat_unavailable")
    fired: list[str] = []
    async with async_session_factory() as session:
        health = await system_health.collect(session, settings)
        by_name = {c.name: c for c in health.components}
        pct = health.disk.used_pct
        if pct is not None and pct > system_health.DISK_ALERT_PCT:
            fired.append("disk_high")
            await admin_alert(session, cid, "disk_high", {})
        if by_name["workers"].status == "down":
            fired.append("worker_down")
            await admin_alert(session, cid, "worker_down", {})
        _, err = await system_health.smtp_state(session, cid)
        if err:
            fired.append("email_failing")
            await admin_alert(session, cid, "email_failing", {})
        await session.commit()
    return fired


@celery_app.task(name="app.tasks.health_tasks.check", queue="maintenance")
def check() -> dict[str, list[str]]:
    """
    @brief Write ``beat:last_run`` and fire disk/worker/email alerts (deduped downstream).

    @return Dict with the alert kinds raised this run.
    """
    return {"alerts": asyncio.run(_check_async())}
