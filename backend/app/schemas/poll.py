"""
@file poll.py
@brief Pydantic schemas for polls, options, and votes.

Defines request/response models used by the polls API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PollOptionCreate(BaseModel):
    """@brief Schema for creating a poll option."""

    label: str = Field(..., min_length=1, max_length=200)
    image_media_id: UUID | None = None


class PollCreate(BaseModel):
    """@brief Schema for creating a poll."""

    question: str = Field(..., min_length=1, max_length=500)
    poll_type: Literal["single", "multiple", "yes_no", "photo"] = "single"
    options: list[PollOptionCreate] = Field(..., min_length=2, max_length=10)
    expires_at: datetime | None = None
    is_anonymous: bool = False
    result_visibility: Literal["after_vote", "always", "after_expiry"] = "after_vote"


class PollVoter(BaseModel):
    """@brief Lightweight voter summary shown on non-anonymous polls."""

    id: UUID
    display_name: str
    avatar_url: str | None = None


class PollOptionResponse(BaseModel):
    """@brief Poll option with vote count in response."""

    id: UUID
    label: str
    image_media_id: UUID | None
    position: int
    vote_count: int = 0
    voters: list[PollVoter] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PollResponse(BaseModel):
    """@brief Full poll object returned by the polls API."""

    id: UUID
    post_id: UUID | None
    poll_type: str
    question: str
    options: list[PollOptionResponse]
    is_anonymous: bool
    result_visibility: str
    expires_at: datetime | None
    closed: bool
    total_votes: int = 0
    user_vote: list[UUID] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VoteRequest(BaseModel):
    """@brief Schema for casting a vote."""

    option_ids: list[UUID] = Field(..., min_length=1)


class PollResultsResponse(BaseModel):
    """@brief Poll results with vote counts per option."""

    poll_id: UUID
    options: list[PollOptionResponse]
    total_votes: int
