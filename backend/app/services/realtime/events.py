"""
@file events.py
@brief Typed event definitions for the real-time pub/sub system.

Provides a single source of truth for all SSE/WebSocket event types,
routing targets, and event builder functions.  Services emit events
via the :class:`EventBus` using these builders instead of constructing
raw dicts.

Usage::

    from app.services.realtime.events import post_created, CommunityTarget

    event = post_created(CommunityTarget(community_id=cid), enriched_post)
    await emit_to_audience(event_bus, audience, event.type, event.payload)
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class EventType(StrEnum):
    """@brief Top-level SSE event type names (wire format)."""

    FEED_UPDATE = "feed_update"
    FEED_PING = "feed_ping"
    NOTIFICATION = "notification"
    USER_NOTIFICATION_DISMISSED = "user_notification_dismissed"
    TYPING = "typing"
    PRESENCE = "presence"


class FeedEvent(StrEnum):
    """@brief Sub-event discriminator within ``feed_update`` payloads."""

    POST_CREATED = "created"
    COMMENT_CREATED = "comment_created"
    REACTION_TOGGLED = "reaction_toggled"
    POLL_VOTED = "poll_voted"
    LIST_EXPIRED = "list_expired"


# ── Routing targets ──────────────────────────────────────────────────────


class EventTarget(BaseModel):
    """@brief Base class for event routing targets."""


class UserTarget(EventTarget):
    """
    @brief Route to a specific user's connections.

    @param user_id UUID of the target user.
    """

    user_id: UUID


class CommunityTarget(EventTarget):
    """
    @brief Route to all users in a community.

    @param community_id UUID of the target community.
    """

    community_id: UUID


# ── Event envelope ───────────────────────────────────────────────────────


class RealtimeEvent(BaseModel):
    """
    @brief Immutable envelope carrying a typed event with routing info.

    @param type Top-level SSE event type.
    @param target Routing target (user or community).
    @param payload JSON-serializable data sent to clients.
    """

    type: EventType
    target: EventTarget
    payload: dict[str, Any]


# ── Builder functions ────────────────────────────────────────────────────


def post_created(target: EventTarget, post: dict[str, Any]) -> RealtimeEvent:
    """
    @brief Build a feed_update event for a newly created post.

    @param target Routing target (see :mod:`audience`).
    @param post Enriched post dict.
    """
    return RealtimeEvent(
        type=EventType.FEED_UPDATE,
        target=target,
        payload={"event": FeedEvent.POST_CREATED, "post": post},
    )


def comment_created(
    target: EventTarget,
    post_id: UUID,
    comment: dict[str, Any],
    user_id: UUID,
) -> RealtimeEvent:
    """
    @brief Build a feed_update event for a new comment.

    @param target Routing target (see :mod:`audience`).
    @param post_id ID of the parent post.
    @param comment Serialized comment dict.
    @param user_id Author of the comment.
    """
    return RealtimeEvent(
        type=EventType.FEED_UPDATE,
        target=target,
        payload={
            "event": FeedEvent.COMMENT_CREATED,
            "post_id": str(post_id),
            "comment": comment,
            "user_id": str(user_id),
        },
    )


def reaction_toggled(
    target: EventTarget,
    post_id: UUID,
    target_type: str,
    target_id: UUID,
    emoji: str,
    count: int,
    action: str,
    user_id: UUID,
) -> RealtimeEvent:
    """
    @brief Build a feed_update event for a reaction toggle.

    @param target Routing target (see :mod:`audience`).
    @param post_id ID of the parent post.
    @param target_type "post" or "comment".
    @param target_id ID of the reacted entity.
    @param emoji Emoji string.
    @param count Updated reaction count.
    @param action "added" or "removed".
    @param user_id User who toggled the reaction.
    """
    return RealtimeEvent(
        type=EventType.FEED_UPDATE,
        target=target,
        payload={
            "event": FeedEvent.REACTION_TOGGLED,
            "post_id": str(post_id),
            "target_type": target_type,
            "target_id": str(target_id),
            "emoji": emoji,
            "count": count,
            "action": action,
            "user_id": str(user_id),
        },
    )


def user_notification(
    user_id: UUID,
    notification_id: UUID,
    notification_type: str,
    payload: dict[str, Any],
    created_at: str,
    *,
    updated_at: str | None = None,
    count: int = 1,
    actor_ids: Sequence[UUID] | None = None,
) -> RealtimeEvent:
    """
    @brief Build a notification event targeted at a single user.

    @param user_id Recipient user UUID.
    @param notification_id DB notification ID.
    @param notification_type Notification type key (mention, comment, etc.).
    @param payload Notification content.
    @param created_at ISO 8601 timestamp.
    @param updated_at ISO 8601 last-update timestamp (defaults to created_at).
    @param count Grouped occurrence count.
    @param actor_ids Actors folded into the notification.
    """
    return RealtimeEvent(
        type=EventType.NOTIFICATION,
        target=UserTarget(user_id=user_id),
        payload={
            "id": str(notification_id),
            "type": notification_type,
            "payload": payload,
            "created_at": created_at,
            "updated_at": updated_at or created_at,
            "count": count,
            "actor_ids": [str(a) for a in actor_ids or ()],
        },
    )


def user_notification_dismissed(
    user_id: UUID,
    notification_ids: Sequence[UUID],
) -> RealtimeEvent:
    """
    @brief Build an event telling a user's other tabs notifications were dismissed.

    @param user_id User who dismissed (sole recipient).
    @param notification_ids Dismissed notification UUIDs.
    """
    return RealtimeEvent(
        type=EventType.USER_NOTIFICATION_DISMISSED,
        target=UserTarget(user_id=user_id),
        payload={
            "user_id": str(user_id),
            "notification_ids": [str(n) for n in notification_ids],
        },
    )


def poll_voted(
    target: EventTarget,
    post_id: UUID | None,
    poll_id: UUID,
    results: dict[str, Any],
) -> RealtimeEvent:
    """
    @brief Build a feed_update event for a poll vote.

    @param target Routing target (see :mod:`audience`).
    @param post_id ID of the parent post (if any).
    @param poll_id ID of the poll.
    @param results Serialized poll results.
    """
    return RealtimeEvent(
        type=EventType.FEED_UPDATE,
        target=target,
        payload={
            "event": FeedEvent.POLL_VOTED,
            "post_id": str(post_id) if post_id else None,
            "poll_id": str(poll_id),
            "results": results,
        },
    )


def typing_indicator(
    community_id: UUID,
    user_id: UUID,
) -> RealtimeEvent:
    """
    @brief Build a typing indicator event for a community.

    @param community_id Community to broadcast to.
    @param user_id User who is typing.
    """
    return RealtimeEvent(
        type=EventType.TYPING,
        target=CommunityTarget(community_id=community_id),
        payload={"user_id": str(user_id)},
    )


def list_expired(target: EventTarget, list_id: UUID, title: str) -> RealtimeEvent:
    """
    @brief Build a feed_update event for a list that has expired.

    @param target Routing target (see :mod:`audience`).
    @param list_id ID of the expired list.
    @param title List title.
    """
    return RealtimeEvent(
        type=EventType.FEED_UPDATE,
        target=target,
        payload={"event": FeedEvent.LIST_EXPIRED, "list_id": str(list_id), "title": title},
    )
