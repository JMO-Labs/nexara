"""
@file inbound_service.py
@brief Turn one inbound reply email into a comment, after re-checking everything
       that could have changed since the notification was sent.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from email.message import Message
from email.utils import parseaddr
from typing import Any, Literal

import structlog

from app.core.exceptions import AppError
from app.core.features import is_enabled
from app.models.user import User
from app.services.email import reply_parse
from app.services.email.reply_address import reply_local_part

logger = structlog.get_logger(__name__)

RATE_LIMIT = 20
"""@brief Email replies allowed per user per hour."""

Outcome = Literal["posted", "ignored"]


class InboundService:
    """@brief Validates and posts one reply email. Never raises for bad mail."""

    def __init__(
        self,
        tokens: Any,
        communities: Any,
        moderation: Any,
        posts: Any,
        post_service: Any,
        session: Any,
        community_id: uuid.UUID,
    ) -> None:
        """
        @param tokens ReplyTokenRepository.
        @param communities CommunityRepository.
        @param moderation ModerationRepository (blocks).
        @param posts PostRepository.
        @param post_service PostService (``add_comment`` applies visibility,
               mentions and notifications).
        @param session Async session (user lookup).
        @param community_id Tenant id.
        """
        self._tokens = tokens
        self._communities = communities
        self._moderation = moderation
        self._posts = posts
        self._post_service = post_service
        self._session = session
        self._cid = community_id

    async def process(self, msg: Message) -> Outcome:
        """
        @brief Post the reply as a comment when every check passes.
        @param msg Parsed inbound message.
        @return ``posted`` or ``ignored`` (the caller deletes the mail either way).
        """
        community = await self._communities.get(self._cid)
        if community is None or not is_enabled(community, "reply_by_email"):
            return "ignored"
        base = reply_local_part(community.inbound_reply_address)
        if base is None or reply_parse.is_auto_reply(msg):
            return "ignored"
        headers = [
            str(v)
            for h in ("To", "Cc", "Delivered-To", "X-Original-To", "Envelope-To")
            for v in (msg.get_all(h) or [])
        ]
        raw = reply_parse.extract_token(headers, base)
        row = await self._tokens.get(raw) if raw else None
        now = datetime.now(UTC)
        if row is None or row.expires_at <= now or row.community_id != self._cid:
            return "ignored"
        user = await self._session.get(User, row.user_id)
        if not self._user_ok(user, reply_parse.sender_address(msg)):
            return "ignored"
        assert user is not None
        post = await self._posts.get_by_id(row.post_id, community_id=self._cid)
        if post is None or (
            post.author_id and await self._moderation.is_blocked_either(post.author_id, user.id)
        ):
            return "ignored"
        body = reply_parse.clean_body(msg)
        if body is None:
            return "ignored"
        if await self._tokens.count_replies_since(user.id, now - timedelta(hours=1)) >= RATE_LIMIT:
            logger.warning("inbound_reply_rate_limited", user_id=str(user.id))
            return "ignored"
        try:
            await self._post_service.add_comment(row.post_id, user, body)
        except AppError:  # post hidden from the user now, etc.
            return "ignored"
        await self._tokens.log_reply(user.id)
        logger.info("inbound_reply_posted", user_id=str(user.id), post_id=str(row.post_id))
        return "posted"

    @staticmethod
    def _user_ok(user: User | None, sender: str | None) -> bool:
        """@brief Active, not memorialized, and the mail really comes from them."""
        if user is None or not user.is_active or user.deleted_at or user.memorialized_at:
            return False
        return bool(sender) and parseaddr(user.email)[1].lower() == sender
