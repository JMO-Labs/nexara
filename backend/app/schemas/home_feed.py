"""
@file home_feed.py
@brief Schemas for the unified home feed (posts + activity).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.activity import ActivityItem


class PostFeedItem(BaseModel):
    """@brief A post card; `post` is the enriched dict `GET /posts` returns."""

    kind: Literal["post"] = "post"
    id: UUID
    created_at: datetime
    post: dict[str, Any]


class ActivityFeedItem(BaseModel):
    """@brief A one-line activity entry."""

    kind: Literal["activity"] = "activity"
    id: UUID
    created_at: datetime
    activity: ActivityItem


FeedItem = Annotated[PostFeedItem | ActivityFeedItem, Field(discriminator="kind")]


class HomeFeedResponse(BaseModel):
    """@brief One page of the merged feed; `next_cursor` is an ISO timestamp."""

    items: list[FeedItem]
    next_cursor: str | None = None
