"""
@file recap_tasks.py
@brief Family recap email: hourly dispatch (beat, ``default`` queue) and the
       per-user send (``email`` queue).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from app.core.config import get_settings
from app.core.security import create_purpose_token
from app.db.session import async_session_factory
from app.models.user import User
from app.repositories.branding_repo import BrandingRepository
from app.services.email.sender import send_email
from app.services.email.smtp_settings import resolve_smtp
from app.services.email.templates import EmailTemplateRenderer
from app.services.recap_service import UNSUBSCRIBE_TTL, RecapService
from app.tasks.celery_app import celery_app
from app.tasks.notification_tasks import _branding_kwargs

logger = structlog.get_logger(__name__)

UNSUB_PURPOSE = "recap_unsub"
"""@brief Token purpose for the unsubscribe link."""


async def _dispatch_async(now: datetime) -> list[uuid.UUID]:
    """@brief Stamp and return due user ids in one committed transaction."""
    cid = uuid.UUID(get_settings().COMMUNITY_ID)
    async with async_session_factory() as session:
        ids = await RecapService(session, cid).due_user_ids(now)
        await session.commit()
    return ids


async def _send_async(user_id: uuid.UUID) -> dict[str, str]:
    """@brief Build, render and send one recap; skip when there is nothing to say."""
    cid = uuid.UUID(get_settings().COMMUNITY_ID)
    base = get_settings().APP_BASE_URL.rstrip("/")
    async with async_session_factory() as session:
        user = await session.get(User, user_id)
        if user is None or user.deleted_at is not None or not user.is_active:
            return {"status": "skipped"}
        sections: list[dict[str, Any]] = [
            dict(s) for s in await RecapService(session, cid).build(user)
        ]
        if not sections:
            return {"status": "skipped"}
        branding = await BrandingRepository(session).get(user.community_id)
        to_email = user.email
        cfg = await resolve_smtp(session, user.community_id)
    if cfg is None:
        return {"status": "skipped"}
    for s in sections:
        for item in s["items"]:
            if item.get("link", "").startswith("/"):
                item["link"] = base + item["link"]
    token = create_purpose_token(user_id, UNSUB_PURPOSE, UNSUBSCRIBE_TTL)
    unsub = f"{base}/api/v1/recap/unsubscribe?token={token}"
    html, text = EmailTemplateRenderer().render(
        "recap.html",
        {
            "sections": sections,
            "unsubscribe_url": unsub,
            "settings_url": f"{base}/app/settings?tab=notifications",
            "app_url": base,
        },
        **_branding_kwargs(branding),
    )
    await send_email(
        cfg,
        to_email,
        "Your family recap",
        html,
        text,
        list_unsubscribe=f"<{unsub}>",
        sender_name=getattr(branding, "email_sender_name", None) or None,
    )
    return {"status": "sent"}


@celery_app.task(name="app.tasks.recap_tasks.send_recap_email", queue="email")
def send_recap_email(user_id: str) -> dict[str, str]:
    """
    @brief Send one user's recap.
    @param user_id UUID string.
    @return ``{"status": "sent" | "skipped"}``.
    """
    return asyncio.run(_send_async(uuid.UUID(user_id)))


@celery_app.task(name="app.tasks.recap_tasks.recap_dispatch", queue="default")
def recap_dispatch() -> int:
    """
    @brief Beat entry (hourly at :10): enqueue recaps for users whose local
           slot is now. Stamps ``recap_last_sent_at`` first so reruns are no-ops.
    @return Number enqueued.
    """
    ids = asyncio.run(_dispatch_async(datetime.now(UTC)))
    for uid in ids:
        send_recap_email.delay(str(uid))
    logger.info("recap_dispatch", enqueued=len(ids))
    return len(ids)
