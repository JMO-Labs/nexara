"""
@file moderation.py
@brief Pydantic schemas for content reporting and user blocking.

Phase 1 delivers schema and repository only; moderation UI ships in Phase 2.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BlockCreate(BaseModel):
    """@brief Request to block another user."""

    blocked_id: UUID = Field(description="UUID of the user to block")


class BlockResponse(BaseModel):
    """@brief Confirmation that a block was created."""

    id: UUID
    blocker_id: UUID
    blocked_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportCreate(BaseModel):
    """@brief Request to report a piece of content."""

    target_type: str = Field(
        ...,
        pattern=r"^(post|comment|message|media)$",
        description="Content type being reported",
    )
    target_id: UUID = Field(description="UUID of the reported content")
    reason: str = Field(
        ...,
        pattern=r"^(spam|harassment|inappropriate|misinformation|other)$",
        description="Report reason",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional additional details from the reporter",
    )


class ReportAction(BaseModel):
    """@brief Admin decision on a report."""

    action: str = Field(
        ...,
        pattern=r"^(dismiss|warn_user|hide_content|delete_content|ban_user)$",
    )
    note: str | None = Field(default=None, max_length=2000)


class ReportActionResponse(BaseModel):
    """@brief Result of an admin action."""

    id: UUID
    status: str
    action_taken: str | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReportCreated(BaseModel):
    """@brief Minimal response after submitting a report."""

    id: UUID
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    """@brief Public representation of a content report."""

    id: UUID
    reporter_id: UUID
    target_type: str
    target_id: UUID
    reason: str
    description: str | None = None
    status: str
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    action_taken: str | None = None
    admin_notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
