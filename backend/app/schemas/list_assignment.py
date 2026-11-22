"""
@file list_assignment.py
@brief Schemas for item assignment requests and the list activity feed.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.list import AssigneeOut, Pagination


class AssignBody(BaseModel):
    """@brief Request body for assigning an item to a member."""

    user_id: uuid.UUID


class ActivityOut(BaseModel):
    """@brief One activity log entry."""

    id: uuid.UUID
    action: str
    actor: AssigneeOut | None = None
    item_id: uuid.UUID | None = None
    item_title: str = ""
    target_user: AssigneeOut | None = None
    created_at: datetime


class ActivityPage(BaseModel):
    """@brief Newest-first page of activity."""

    activity: list[ActivityOut]
    pagination: Pagination
