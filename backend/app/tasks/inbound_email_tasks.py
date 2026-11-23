"""
@file inbound_email_tasks.py
@brief Beat task ``inbound_email.poll``: read the reply mailbox over IMAP (SSL),
       post valid replies as comments, delete processed and ignored mail.

Only runs when the ``reply_by_email`` feature is on and settings are complete.
Network and login errors are logged at warning level (no credentials) and never raised.
"""

from __future__ import annotations

import asyncio
import email
import imaplib
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from app.core.config import get_settings
from app.core.encryption import decrypt_secret, derive_fernet_key
from app.db.session import async_session_factory
from app.repositories.community_repo import CommunityRepository
from app.repositories.moderation_repo import ModerationRepository
from app.repositories.post_repo import PostRepository
from app.repositories.reply_token_repo import ReplyTokenRepository
from app.services.email import imap_client
from app.services.email.inbound_service import InboundService
from app.services.email.reply_address import is_active
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _handle(session: Any, cid: uuid.UUID, raw: bytes) -> str:
    """@brief Process one raw message in its own transaction; never raises."""
    from app.api.v1.posts import _build_service  # same wiring as the comment route

    try:
        service = InboundService(
            ReplyTokenRepository(session),
            CommunityRepository(session),
            ModerationRepository(session),
            PostRepository(session),
            _build_service(session, cid, get_settings()),
            session,
            cid,
        )
        outcome: str = await service.process(email.message_from_bytes(raw))
        await session.commit()
        return outcome
    except Exception as exc:
        await session.rollback()
        logger.warning("inbound_email_message_failed", error=type(exc).__name__)
        return "ignored"


async def _poll_async() -> dict[str, int]:
    """@brief One poll: fetch up to 50 unseen mails, process, delete."""
    settings = get_settings()
    cid = uuid.UUID(settings.COMMUNITY_ID)
    async with async_session_factory() as session:
        community = await CommunityRepository(session).get(cid)
        if community is None or not is_active(community):
            return {"posted": 0, "ignored": 0}
        host, port, user = (
            community.inbound_imap_host or "",
            community.inbound_imap_port,
            community.inbound_imap_user or "",
        )
        password = decrypt_secret(
            community.inbound_imap_password or "", derive_fernet_key(settings.SECRET_KEY)
        )
        await ReplyTokenRepository(session).purge(datetime.now(UTC))
        await session.commit()
    counts = {"posted": 0, "ignored": 0}
    try:
        conn, messages = await asyncio.to_thread(
            imap_client.fetch_unseen, host, port, user, password
        )
    except (imaplib.IMAP4.error, OSError) as exc:
        logger.warning("inbound_email_poll_failed", error=type(exc).__name__)
        return counts
    try:
        for _num, raw in messages:
            async with async_session_factory() as session:
                counts[await _handle(session, cid, raw)] += 1
    finally:
        try:
            await asyncio.to_thread(imap_client.finish, conn, [n for n, _ in messages])
        except (imaplib.IMAP4.error, OSError) as exc:
            logger.warning("inbound_email_cleanup_failed", error=type(exc).__name__)
    return counts


@celery_app.task(name="inbound_email.poll", queue="email")
def poll() -> dict[str, int]:
    """@brief Beat-driven entry, every minute."""
    return asyncio.run(_poll_async())
