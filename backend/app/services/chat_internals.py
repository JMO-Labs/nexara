"""
@file chat_internals.py
@brief Broadcast, link-preview and rate-limit internals for ChatService.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import structlog

from app.core.exceptions import AuthorizationError, RateLimitError
from app.core.i18n import _
from app.models.subgroup import ChatChannel
from app.repositories.chat_repo import ChatChannelRepository
from app.repositories.moderation_repo import ModerationRepository
from app.services.chat_helpers import CHAT_RATE_LIMIT_PER_MINUTE, channel_pubsub_name
from app.services.link_preview_service import extract_urls

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = structlog.get_logger(__name__)


class ChatInternalsMixin:
    """@brief Private helpers mixed into :class:`ChatService`."""

    _channel_repo: ChatChannelRepository
    _community_id: uuid.UUID
    _rate_limiter: Redis | None
    _broadcaster: Any
    _link_preview_enqueue: Any
    _moderation_repo: ModerationRepository | None

    async def _broadcast(
        self,
        channel_id: uuid.UUID,
        type_: str,
        payload: dict[str, Any],
        *,
        channel: ChatChannel | None = None,
    ) -> int:
        """
        @brief Publish a typed envelope to every member of the channel.

        Fans out via per-user pub/sub (``user:{uid}``) so the realtime
        subscriber, which psubscribes ``user:*``/``community:*``, routes
        each frame to the correct WebSocket connections. Falls back to
        the legacy ``chat:{channel_id}`` topic when the channel cannot
        be resolved (preserves backwards-compat for any external
        listener still using it).
        """
        if self._broadcaster is None:
            from app.services.realtime.pubsub import publish as default_publish

            publish = default_publish
        else:
            publish = self._broadcaster

        message = {"type": type_, "payload": payload}

        ch = channel
        if ch is None:
            ch = await self._channel_repo.get(channel_id, self._community_id)
        if ch is None:
            return await publish(channel_pubsub_name(channel_id), message)

        member_ids = await self._channel_repo.list_member_ids(
            ch,
            self._community_id,
        )

        total = 0
        for uid in member_ids:
            total += await publish(f"user:{uid}", message)
        return total

    async def _enqueue_link_previews(
        self,
        content: str,
        message_id: uuid.UUID,
    ) -> None:
        """@brief Dispatch a Celery task per URL found in ``content``."""
        urls = extract_urls(content)
        if not urls:
            return

        if self._link_preview_enqueue is None:
            try:
                from app.tasks.link_preview_tasks import scrape_link_preview

                enqueue = scrape_link_preview.delay
            except Exception:
                logger.warning("chat_link_preview_task_unavailable", exc_info=True)
                return
        else:
            enqueue = self._link_preview_enqueue

        for url in urls:
            try:
                enqueue(url, message_id=str(message_id))
            except Exception:
                logger.warning(
                    "chat_link_preview_enqueue_failed",
                    url=url,
                    message_id=str(message_id),
                    exc_info=True,
                )

    async def _enforce_rate_limit(self, user_id: uuid.UUID) -> None:
        """
        @brief Enforce 30 msg/min/user via Valkey ``INCR`` + ``EXPIRE``.

        Silently passes when no Valkey client is configured (e.g. tests).
        """
        if self._rate_limiter is None:
            return
        key = f"rl:chat:send:{user_id}"
        try:
            count = await self._rate_limiter.incr(key)
            if count == 1:
                await self._rate_limiter.expire(key, 60)
        except Exception:
            logger.debug("chat_rate_limit_backend_unavailable", exc_info=True)
            return

        if count > CHAT_RATE_LIMIT_PER_MINUTE:
            raise RateLimitError(_("Chat rate limit exceeded"))

    async def _ensure_not_blocked(self, sender_id: uuid.UUID, peer_id: uuid.UUID) -> None:
        """
        @brief Reject DM activity when either user has blocked the other.

        @raises AuthorizationError If a block exists in either direction.
        """
        if self._moderation_repo is None:
            return
        if await self._moderation_repo.is_blocked_either(sender_id, peer_id):
            raise AuthorizationError(_("Cannot send message to this user"))

    async def _ensure_dm_not_blocked(self, channel: ChatChannel, user_id: uuid.UUID) -> None:
        """
        @brief Apply :meth:`_ensure_not_blocked` to the peer of a DM channel.

        @param channel Target channel; non-DM channels are ignored.
        @param user_id Acting user.
        """
        if getattr(channel, "channel_type", None) != "direct":
            return
        peer_id = await self._channel_repo.get_dm_peer_id(channel.id, user_id)
        if peer_id is not None:
            await self._ensure_not_blocked(user_id, peer_id)
