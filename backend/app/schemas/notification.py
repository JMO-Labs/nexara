"""
@file notification.py
@brief Pydantic schemas for notification API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, get_args
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    """
    @brief Single notification item returned by the API.

    @param id UUID of the notification.
    @param user_id UUID of the recipient.
    @param type Notification type (mention, comment, reaction, etc.).
    @param payload JSON payload with message, link, actor info.
    @param read_at Timestamp when marked read, or None.
    @param created_at Creation timestamp.
    @param updated_at Last update (grouped merges bump it).
    @param dismissed_at Timestamp when dismissed from the bell, or None.
    @param count Number of grouped occurrences.
    @param actor_ids Actors folded into this notification.
    """

    id: UUID
    user_id: UUID
    type: str
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime | None = None
    dismissed_at: datetime | None = None
    count: int = 1
    actor_ids: list[UUID] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class NotificationList(BaseModel):
    """
    @brief Cursor-paginated list of notifications.

    @param items Page of notification items.
    @param next_cursor Opaque cursor for the next page, or None.
    @param has_more Whether more results exist.
    """

    items: list[NotificationResponse]
    next_cursor: str | None = None
    has_more: bool = False


class UnreadCountResponse(BaseModel):
    """
    @brief Unread notification count for badge display.

    @param count Total unread.
    @param by_category Unread count per registry category (non-zero only).
    """

    count: int
    by_category: dict[str, int] = Field(default_factory=dict)


DigestCadence = Literal["instant", "hourly", "daily", "off"]
"""@brief Allowed per-type digest cadence values."""

DIGEST_CADENCES: tuple[str, ...] = get_args(DigestCadence)


class NotificationPreferences(BaseModel):
    """
    @brief Per-user notification preferences (v2 JSONB + DnD + digest).

    @param notification_prefs {type_key: {channel: bool}} overrides.
    @param dnd_schedule Weekly quiet-hours schedule, or None.
    @param dnd_until Snooze end, or None.
    @param dnd_timezone IANA zone for the schedule.
    @param digest_cadence {type_key: cadence}.
    """

    notification_prefs: dict[str, dict[str, bool]]
    dnd_schedule: dict[str, Any] | None
    dnd_until: datetime | None
    dnd_timezone: str
    digest_cadence: dict[str, str]

    model_config = {"from_attributes": True}


class NotificationPreferencesUpdate(BaseModel):
    """
    @brief Partial update; only fields present in the body are applied.

    Values are validated against the registry in the service layer.
    """

    notification_prefs: dict[str, dict[str, Any]] | None = None
    dnd_schedule: dict[str, Any] | None = None
    dnd_timezone: str | None = None
    digest_cadence: dict[str, str] | None = None
