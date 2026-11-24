"""@file admin_alerts.py
@brief Alert admins (admin Apprise targets + in-app ``system`` notification).

Deduped per ``(kind, key)`` for 30 minutes in Valkey. If Valkey is unreachable the
alert is sent anyway: a duplicate is better than a missed alert. Never raises.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.valkey import DB_CACHE, get_pool
from app.models.user import User
from app.repositories.apprise_repo import AppriseRepository
from app.services.notifications.apprise_guard import build_apprise
from app.services.notifications.factory import build_notification_service

logger = structlog.get_logger(__name__)

DEDUPE_SECONDS = 1800
_MESSAGES = {
    "signin_burst": "Repeated failed sign-ins from {ip}",
    "disk_high": "Disk usage is high",
    "worker_down": "A background worker is down",
    "email_failing": "Outgoing email is failing",
}


def _message(kind: str, data: dict[str, Any]) -> str:
    try:
        return _MESSAGES.get(kind, kind).format(**data)
    except (KeyError, IndexError):
        return _MESSAGES.get(kind, kind)


async def _deliver(session: AsyncSession, community_id: uuid.UUID, kind: str, msg: str) -> None:
    for t in await AppriseRepository(session).list_admin_targets(community_id):
        try:
            apobj = build_apprise(t.apprise_url, allow_local=True)
            ok = await asyncio.to_thread(apobj.notify, body=msg, title="Nexara alert")
            if not ok:
                logger.warning("admin_alert.apprise_failed", target_id=str(t.id))
        except Exception as exc:
            logger.warning(
                "admin_alert.apprise_failed", target_id=str(t.id), error=type(exc).__name__
            )
    svc = build_notification_service(session, community_id)
    admins = (
        (
            await session.execute(
                select(User.id).where(
                    User.community_id == community_id,
                    User.role == "admin",
                    User.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for uid in admins:
        try:
            await svc.notify(uid, "system", {"message": msg})
        except Exception:
            logger.warning("admin_alert.notify_failed", kind=kind, exc_info=True)


async def admin_alert(
    session: AsyncSession, community_id: uuid.UUID, kind: str, data: dict[str, Any]
) -> None:
    """
    @brief Notify admins about ``kind`` unless the same alert fired in the last 30 min.

    @param session DB session.
    @param community_id Tenant scope.
    @param kind ``signin_burst`` | ``disk_high`` | ``worker_down`` | ``email_failing``.
    @param data Context; ``ip`` (else ``key``) distinguishes dedupe keys.
    """
    key = str(data.get("ip") or data.get("key") or "-")
    try:
        redis = get_pool(get_settings(), DB_CACHE)
        if not await redis.set(f"admin_alert:{kind}:{key}", "1", nx=True, ex=DEDUPE_SECONDS):
            return
    except Exception:
        logger.warning("admin_alert.dedupe_unavailable", kind=kind)
    try:
        await _deliver(session, community_id, kind, _message(kind, data))
    except Exception:
        logger.warning("admin_alert.failed", kind=kind, exc_info=True)
