"""
@file activity.py
@brief Pydantic schemas for activity feed responses.

ActivityItem represents a single (possibly aggregated) feed entry;
ActivityFeedResponse wraps a list of items with pagination cursor.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ActivityItem(BaseModel):
    """
    @brief A single activity feed entry (possibly aggregated).

    Represents one or more events collapsed within a 60-minute window
    (same actor, verb, target).
    """

    id: UUID = Field(..., description="Newest event ID in this aggregate")
    actor_id: UUID = Field(..., description="UUID of user who triggered the event")
    actor_name: str = Field(..., description="Actor display name from metadata snapshot")
    verb: str = Field(..., description="Action verb, e.g. 'post.created'")
    object_type: str = Field(..., description="Type of object, e.g. 'post', 'media'")
    object_id: UUID = Field(..., description="UUID of affected object (for link resolution)")
    container_type: str | None = Field(
        None, description="Container type: 'subgroup', 'community', or None"
    )
    container_title: str | None = Field(
        None, description="Container display name from metadata snapshot"
    )
    object_title: str | None = Field(None, description="Object title from metadata snapshot")
    count: int = Field(default=1, ge=1, description="Number of events in this aggregate")
    created_at: datetime = Field(..., description="Timestamp of newest event in aggregate")


class ActivityFeedResponse(BaseModel):
    """
    @brief Paginated response of activity feed items.

    Includes list of items and an optional cursor for fetching the next page.
    """

    items: list[ActivityItem] = Field(default_factory=list, description="Activity feed items")
    next_cursor: datetime | None = Field(
        None, description="Cursor for next page (created_at of last item)"
    )
