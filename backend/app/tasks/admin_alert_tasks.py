"""
@file admin_alert_tasks.py
@brief Celery task delivering admin alerts to Apprise targets off the request path.

Routed to the ``notifications`` queue.
"""

from __future__ import annotations

import asyncio
import uuid

from app.db.session import async_session_factory
from app.services.admin_alerts import deliver_apprise
from app.tasks.celery_app import celery_app


async def _send(community_id: str, msg: str) -> None:
    async with async_session_factory() as session:
        await deliver_apprise(session, uuid.UUID(community_id), msg)


@celery_app.task(name="app.tasks.admin_alert_tasks.send_apprise_alert", queue="notifications")
def send_apprise_alert(community_id: str, msg: str) -> None:
    """
    @brief Send an already-deduped admin alert to admin Apprise targets.

    @param community_id Tenant UUID string.
    @param msg Alert text.
    """
    asyncio.run(_send(community_id, msg))
