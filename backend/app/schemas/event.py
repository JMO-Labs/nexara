"""
@file event.py
@brief Pydantic schemas for events, RSVP, contributions, and calendar subscriptions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

VisibilityType = Literal["community", "subgroup", "private"]
RSVPStatus = Literal["attending", "maybe", "declined"]


class ContributionSlot(BaseModel):
    """@brief A "who's bringing what" slot on an event."""

    id: UUID | None = None
    title: str = Field(..., min_length=1, max_length=200)
    quantity_needed: int = Field(default=1, ge=1, le=999)
    quantity_claimed: int = Field(default=0, ge=0)
    claimed_by: list[UUID] = Field(default_factory=list)


class EventCreate(BaseModel):
    """@brief Schema for creating an event."""

    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = Field(None, max_length=10_000)
    location: str | None = Field(None, max_length=500)
    starts_at: datetime
    ends_at: datetime
    is_all_day: bool = False
    recurrence_rule: str | None = Field(None, max_length=500)
    visibility: VisibilityType = "community"
    subgroup_id: UUID | None = None
    rsvp_labels: dict[str, str] | None = None
    contribution_slots: list[ContributionSlot] = Field(default_factory=list)

    @field_validator("ends_at")
    @classmethod
    def _ends_after_starts(cls, v: datetime, info: Any) -> datetime:
        starts = info.data.get("starts_at")
        if starts and v < starts:
            raise ValueError("ends_at must be on or after starts_at")
        return v


class EventUpdate(BaseModel):
    """@brief Schema for updating an event (all fields optional)."""

    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = Field(None, max_length=10_000)
    location: str | None = Field(None, max_length=500)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_all_day: bool | None = None
    recurrence_rule: str | None = Field(None, max_length=500)
    visibility: VisibilityType | None = None
    subgroup_id: UUID | None = None
    rsvp_labels: dict[str, str] | None = None
    contribution_slots: list[ContributionSlot] | None = None


class RSVPRequest(BaseModel):
    """@brief Schema for casting an RSVP."""

    status: str = Field(..., min_length=1, max_length=50)
    note: str | None = Field(None, max_length=500)


class RSVPResponse(BaseModel):
    """@brief Single RSVP record."""

    id: UUID
    event_id: UUID
    user_id: UUID
    status: str
    note: str | None
    responded_at: datetime

    model_config = {"from_attributes": True}


class EventResponse(BaseModel):
    """@brief Full event object returned by the API."""

    id: UUID
    author_id: UUID
    title: str
    description: str | None
    location: str | None
    starts_at: datetime
    ends_at: datetime
    is_all_day: bool
    recurrence_rule: str | None
    recurrence_id: UUID | None
    ical_uid: str
    visibility: str
    subgroup_id: UUID | None
    rsvp_labels: dict[str, str] | None
    contribution_slots: list[ContributionSlot] = Field(default_factory=list)
    rsvp_counts: dict[str, int] = Field(default_factory=dict)
    user_rsvp: RSVPResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventOccurrence(BaseModel):
    """@brief Expanded occurrence of a recurring event."""

    event_id: UUID
    starts_at: datetime
    ends_at: datetime


class EventList(BaseModel):
    """@brief Paginated event list."""

    items: list[EventResponse]
    next_cursor: str | None = None
    has_more: bool = False


class ContributionClaim(BaseModel):
    """@brief Schema for claiming a contribution slot."""

    quantity: int = Field(default=1, ge=1, le=99)


class CalendarSubscriptionCreate(BaseModel):
    """@brief Schema for subscribing to an external iCal feed."""

    name: str = Field(..., min_length=1, max_length=200)
    color: str = Field(default="#4285f4", pattern=r"^#[0-9A-Fa-f]{6}$")
    source_type: Literal["ical", "google"] = "ical"
    source_url: str = Field(..., min_length=1, max_length=2000)
    visibility: Literal["private", "community"] = "private"


class CalendarSubscriptionResponse(BaseModel):
    """@brief External calendar subscription."""

    id: UUID
    name: str
    color: str
    source_type: str
    source_url: str | None
    visibility: str
    sync_enabled: bool
    last_synced_at: datetime | None
    sync_error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
