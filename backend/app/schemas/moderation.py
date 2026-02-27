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
        ..., pattern=r"^(post|comment|message|media)$",
        description="Content type being reported",
    )
    target_id: UUID = Field(description="UUID of the reported content")
    reason: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(
        default=None, max_length=2000,
        description="Optional additional details from the reporter",
    )


class ReportResponse(BaseModel):
    """@brief Public representation of a content report."""

    id: UUID
    reporter_id: UUID
    target_type: str
    target_id: UUID
    reason: str
    description: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
