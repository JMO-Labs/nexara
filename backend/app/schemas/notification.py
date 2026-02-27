"""
@file notification.py
@brief Pydantic schemas for notification API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """
    @brief Single notification item returned by the API.

    @param id UUID of the notification.
    @param user_id UUID of the recipient.
    @param type Notification type (mention, comment, reaction, etc.).
    @param payload JSON payload with message, link, actor info.
    @param read_at Timestamp when marked read, or None.
    @param created_at Creation timestamp.
    """

    id: UUID
    user_id: UUID
    type: str
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime

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
    """@brief Unread notification count for badge display."""

    count: int
