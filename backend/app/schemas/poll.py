"""
@file poll.py
@brief Pydantic schemas for poll creation, voting, and responses.

Defines request/response models used by the polls API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

PollType = Literal["single", "multiple", "yes_no", "photo"]


class PollOptionCreate(BaseModel):
    """
    @brief Payload for creating a poll option.

    @param label Display text for the option.
    @param image_media_id Optional media UUID for photo-style options.
    @param position Display order (0-based).
    """

    label: str
    image_media_id: UUID | None = None
    position: int = 0


class PollCreate(BaseModel):
    """
    @brief Payload for creating a poll.

    @param question The poll question text.
    @param poll_type One of single, multiple, yes_no, photo.
    @param expires_at Optional expiration datetime.
    @param is_anonymous Whether votes are anonymous.
    @param allow_add_options Whether users can add options.
    @param options Initial options (can be empty for yes_no).
    """

    question: str
    poll_type: PollType
    expires_at: datetime | None = None
    is_anonymous: bool = False
    allow_add_options: bool = False
    options: list[PollOptionCreate] = []


class PollVoteCreate(BaseModel):
    """
    @brief Payload for casting a vote on a poll option.

    @param poll_id The poll being voted on.
    @param option_id The option being selected.
    """

    poll_id: UUID
    option_id: UUID


class PollOptionResponse(BaseModel):
    """
    @brief Poll option in API responses.

    @param vote_count Aggregated vote count for this option.
    """

    id: UUID
    label: str
    image_media_id: UUID | None = None
    position: int
    vote_count: int = 0

    model_config = {"from_attributes": True}


class PollResponse(BaseModel):
    """
    @brief Full poll object returned by the polls API.

    @param options List of options with vote counts.
    @param total_votes Sum of votes across all options.
    """

    id: UUID
    question: str
    poll_type: str
    expires_at: datetime | None = None
    is_anonymous: bool
    allow_add_options: bool
    created_by: UUID | None = None
    options: list[PollOptionResponse] = []
    total_votes: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
