"""
@file chat_service.py
@brief Business logic for chat channels, messages, and direct messaging.

Coordinates the chat repositories with realtime publishing:
  * ``send_message`` persists a :class:`ChatMessage`, publishes a
    ``chat.message`` envelope to the ``chat:{channel_id}`` Valkey pub/sub
    channel, and dispatches a Celery task for each URL detected in the
    message body (link preview generation).
  * ``edit_message`` / ``delete_message`` enforce author-only / admin
    permission rules and broadcast ``chat.updated`` / ``chat.deleted``.
  * ``create_or_get_dm`` returns the canonical DM channel for two users.
  * ``get_history`` returns cursor-paginated message history with the
    block filter applied.

Rate limit: 30 msg/min/user via Valkey sliding-window counter.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.subgroup import ChatChannel
from app.models.user import User
from app.plugins.hooks import HookRegistry
from app.repositories.activity_repo import ActivityRepository
from app.repositories.chat_repo import (
    TOMBSTONE_CONTENT,
    ChatChannelRepository,
    ChatMessageRepository,
)
from app.services.activity_publish import record_activity
from app.services.chat_helpers import (
    CHAT_PUBSUB_CHANNEL_PREFIX,  # noqa: F401  (re-export)
    CHAT_RATE_LIMIT_PER_MINUTE,
    channel_pubsub_name,  # noqa: F401  (re-export)
    serialize_message,
)
from app.services.chat_internals import ChatInternalsMixin

if TYPE_CHECKING:
    from redis.asyncio import Redis


class ChatService(ChatInternalsMixin):
    """
    @brief Service layer for chat channels and message flow.

    @param channel_repo ChatChannelRepository instance.
    @param message_repo ChatMessageRepository instance.
    @param community_id UUID of the active community.
    @param rate_limiter Optional Valkey client for rate-limit counters.
    @param broadcaster Optional async callable publishing a message to a
        pub/sub channel (defaults to :func:`realtime.pubsub.publish`).
    @param link_preview_enqueue Optional callable dispatching a Celery
        task for URL scraping (defaults to the real Celery task).
    """

    def __init__(
        self,
        channel_repo: ChatChannelRepository,
        message_repo: ChatMessageRepository,
        community_id: uuid.UUID,
        *,
        rate_limiter: Redis | None = None,
        broadcaster: Any = None,
        link_preview_enqueue: Any = None,
        activity_repo: ActivityRepository | None = None,
    ) -> None:
        self._channel_repo = channel_repo
        self._message_repo = message_repo
        self._community_id = community_id
        self._rate_limiter = rate_limiter
        self._broadcaster = broadcaster
        self._link_preview_enqueue = link_preview_enqueue
        self._activity_repo = activity_repo

    # ── Channel management ───────────────────────────────────────────

    async def list_channels(self, user: User) -> list[ChatChannel]:
        """
        @brief Return every channel the given user is permitted to see.

        @param user Requesting user.
        @return List of ChatChannel rows.
        """
        return await self._channel_repo.list_for_user(user.id, self._community_id)

    async def create_or_get_dm(
        self,
        user: User,
        peer_id: uuid.UUID,
    ) -> ChatChannel:
        """
        @brief Return (creating if necessary) the DM channel between two users.

        @param user Requesting user.
        @param peer_id Other user's UUID.
        @return The DM ChatChannel.
        @raises NotFoundError If the peer user is missing.
        @raises AuthorizationError If attempting to DM oneself.
        """
        if peer_id == user.id:
            raise AuthorizationError(_("Cannot DM yourself"))

        channel, _created = await self._channel_repo.get_or_create_dm(
            user.id,
            peer_id,
            self._community_id,
        )
        return channel

    async def ensure_subgroup_channel(
        self,
        user: User,
        subgroup_id: uuid.UUID,
    ) -> ChatChannel:
        """
        @brief Return (creating if necessary) the chat channel for a subgroup.

        Caller must be a member of the subgroup. Validates membership via
        :class:`SubgroupMember` before touching the channel table.

        @param user Requesting user.
        @param subgroup_id Subgroup UUID.
        @return The subgroup ChatChannel.
        @raises AuthorizationError If user is not a subgroup member.
        @raises NotFoundError If the subgroup does not exist.
        """
        from sqlalchemy import select as _select

        from app.models.subgroup import Subgroup, SubgroupMember

        session = self._channel_repo._session
        sg = await session.execute(
            _select(Subgroup).where(
                Subgroup.id == subgroup_id,
                Subgroup.community_id == self._community_id,
            )
        )
        subgroup = sg.scalar_one_or_none()
        if subgroup is None:
            raise NotFoundError(_("Subgroup not found"))

        membership = await session.execute(
            _select(SubgroupMember).where(
                SubgroupMember.subgroup_id == subgroup_id,
                SubgroupMember.user_id == user.id,
            )
        )
        if membership.scalar_one_or_none() is None:
            raise AuthorizationError(_("Not a member of this subgroup"))

        channel, _created = await self._channel_repo.get_or_create_subgroup(
            subgroup_id,
            self._community_id,
            subgroup.name,
        )
        return channel

    async def list_dm_threads(self, user: User) -> list[dict[str, Any]]:
        """
        @brief Return every DM thread the user participates in.

        @param user Requesting user.
        @return List of dicts ``{channel_id, peer, created_at}``.
        """
        rows = await self._channel_repo.list_dm_threads(user.id, self._community_id)
        threads: list[dict[str, Any]] = []
        for channel, peer in rows:
            threads.append(
                {
                    "channel_id": str(channel.id),
                    "peer": {
                        "id": str(peer.id),
                        "username": peer.username,
                        "display_name": peer.display_name,
                        "avatar_url": peer.avatar_url,
                    },
                    "created_at": channel.created_at.isoformat(),
                }
            )
        return threads

    # ── Message flow ─────────────────────────────────────────────────

    async def send_message(
        self,
        user: User,
        channel_id: uuid.UUID,
        content: str,
    ) -> dict[str, Any]:
        """
        @brief Persist a new chat message, broadcast it, enqueue link previews.

        @param user Authoring user.
        @param channel_id Target channel UUID.
        @param content Message text.
        @return Serialized message dict.
        @raises NotFoundError If the channel is unknown or the user cannot post.
        @raises RateLimitError If the user exceeded :data:`CHAT_RATE_LIMIT_PER_MINUTE`.
        """
        await self._enforce_rate_limit(user.id)

        channel = await self._channel_repo.get_for_user(
            channel_id,
            user.id,
            self._community_id,
        )
        if channel is None:
            raise NotFoundError(_("Channel not found"))

        hook_kw: dict[str, Any] = {
            "community_id": self._community_id,
            "session": self._channel_repo.session,
            "user_id": user.id,
            "channel_id": channel.id,
            "content": content,
        }
        await HookRegistry.emit("before_chat_sent", **hook_kw)

        message = await self._message_repo.create_message(
            community_id=self._community_id,
            channel_id=channel.id,
            author_id=user.id,
            content=content,
        )
        payload = serialize_message(message, user)
        await HookRegistry.emit("after_chat_sent", message_id=message.id, **hook_kw)

        # Record activity with throttling via Redis SETNX (1 per 30 min per user per channel)
        # Only public/subgroup channels surface in feeds; never DMs.
        is_public = getattr(channel, "channel_type", None) in ("community", "subgroup")
        if is_public and self._activity_repo is not None and self._rate_limiter is not None:
            throttle_key = f"activity:chat:throttle:{self._community_id}:{user.id}:{channel.id}"
            setnx_result = await self._rate_limiter.set(throttle_key, "1", nx=True, ex=1800)
            if setnx_result:
                await record_activity(
                    self._activity_repo,
                    self._channel_repo._session,
                    None,
                    community_id=self._community_id,
                    actor_id=user.id,
                    verb="chat.posted",
                    object_type="chat",
                    object_id=message.id,
                    subgroup_id=channel.subgroup_id if hasattr(channel, "subgroup_id") else None,
                    visibility="community"
                    if not hasattr(channel, "subgroup_id") or channel.subgroup_id is None
                    else "subgroup",
                    target_type="channel",
                    target_id=channel.id,
                    metadata={
                        "actor_name": user.display_name,
                        "object_title": channel.name if hasattr(channel, "name") else "Chat",
                    },
                )

        await self._broadcast(channel.id, "chat.message", payload, channel=channel)
        await self._enqueue_link_previews(content, message.id)

        return payload

    async def get_history(
        self,
        user: User,
        channel_id: uuid.UUID,
        *,
        cursor: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        @brief Fetch a paginated page of channel history for the user.

        @param user Requesting user.
        @param channel_id Channel UUID.
        @param cursor Opaque cursor (base64 ``created_at,id``).
        @param limit Max rows to return (1-100).
        @return ``{items, cursor, has_more}``.
        @raises NotFoundError If the channel is unknown or inaccessible.
        """
        channel = await self._channel_repo.get_for_user(
            channel_id,
            user.id,
            self._community_id,
        )
        if channel is None:
            raise NotFoundError(_("Channel not found"))

        rows, next_cursor = await self._message_repo.get_history_paginated(
            channel.id,
            self._community_id,
            viewer_id=user.id,
            cursor=cursor,
            limit=limit,
        )
        items = [serialize_message(msg, author) for msg, author in rows]
        return {
            "items": items,
            "cursor": next_cursor,
            "has_more": next_cursor is not None,
        }

    async def edit_message(
        self,
        user: User,
        message_id: uuid.UUID,
        content: str,
    ) -> dict[str, Any]:
        """
        @brief Edit a message the caller authored and broadcast the update.

        @param user Acting user.
        @param message_id Target message UUID.
        @param content New content.
        @return Serialized message dict.
        @raises NotFoundError If the message is absent.
        @raises AuthorizationError If the caller is not the author.
        """
        message = await self._message_repo.get(message_id, self._community_id)
        if message is None:
            raise NotFoundError(_("Message not found"))
        if message.author_id != user.id:
            raise AuthorizationError(_("You can only edit your own messages"))
        if message.content == TOMBSTONE_CONTENT:
            raise NotFoundError(_("Message has been deleted"))

        updated = await self._message_repo.update_content(message, content)
        payload = serialize_message(updated, user)
        if updated.channel_id is not None:
            await self._broadcast(updated.channel_id, "chat.updated", payload)
        return payload

    async def delete_message(
        self,
        user: User,
        message_id: uuid.UUID,
    ) -> None:
        """
        @brief Soft-delete a message (author or admin) and broadcast a tombstone.

        @param user Acting user.
        @param message_id Target message UUID.
        @raises NotFoundError If the message is absent.
        @raises AuthorizationError If the caller is neither author nor admin.
        """
        message = await self._message_repo.get(message_id, self._community_id)
        if message is None:
            raise NotFoundError(_("Message not found"))

        is_author = message.author_id == user.id
        is_admin = getattr(user, "role", "") == "admin"
        if not (is_author or is_admin):
            raise AuthorizationError(_("You can only delete your own messages"))

        deleted = await self._message_repo.soft_delete_message(message)
        if deleted.channel_id is not None:
            payload = {
                "id": str(deleted.id),
                "channel_id": str(deleted.channel_id),
                "deleted": True,
                "edited_at": deleted.edited_at.isoformat() if deleted.edited_at else None,
            }
            await self._broadcast(deleted.channel_id, "chat.deleted", payload)
        if self._activity_repo is not None:
            await self._activity_repo.invalidate("chat", message_id)

    async def leave_dm(
        self,
        user: User,
        channel_id: uuid.UUID,
    ) -> None:
        """
        @brief Remove the calling user from a DM channel.

        @param user Acting user.
        @param channel_id DM channel UUID.
        @raises NotFoundError If the channel is not a DM the user belongs to.
        """
        channel = await self._channel_repo.get_for_user(
            channel_id,
            user.id,
            self._community_id,
        )
        if channel is None or channel.channel_type != "direct":
            raise NotFoundError(_("Direct message thread not found"))

        await self._channel_repo.remove_dm_participant(channel_id, user.id)

    # ── Internals ────────────────────────────────────────────────────
