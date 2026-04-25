"""
@file prompt.py
@brief Pydantic schemas for tradition prompts and prompt posts.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

FrequencyType = Literal["annual_date", "weekly", "monthly", "one_time", "custom"]
PromptScope = Literal["community", "subgroup"]
PromptSource = Literal["builtin", "custom"]


class PromptCreate(BaseModel):
    """@brief Schema for creating a prompt (admin only)."""

    title: str = Field(..., min_length=1, max_length=300)
    body: str = Field(..., min_length=1, max_length=10_000)
    frequency_type: FrequencyType
    trigger_month: int | None = Field(None, ge=1, le=12)
    trigger_day: int | None = Field(None, ge=1, le=31)
    trigger_weekday: int | None = Field(None, ge=0, le=6)
    trigger_week_interval: int | None = Field(None, ge=1, le=52)
    trigger_month_day: int | None = Field(None, ge=1, le=31)
    trigger_custom_rule: str | None = Field(None, max_length=500)
    trigger_one_time_date: date | None = None
    active_days: int = Field(default=7, ge=1, le=365)
    scope: PromptScope = "community"
    subgroup_id: UUID | None = None
    notify_members: bool = True
    notification_body: str | None = Field(None, max_length=1000)
    linked_event_id: UUID | None = None
    generate_summary: bool = True


class PromptUpdate(BaseModel):
    """@brief Schema for updating a prompt (all fields optional)."""

    title: str | None = Field(None, min_length=1, max_length=300)
    body: str | None = Field(None, min_length=1, max_length=10_000)
    is_enabled: bool | None = None
    frequency_type: FrequencyType | None = None
    trigger_month: int | None = Field(None, ge=1, le=12)
    trigger_day: int | None = Field(None, ge=1, le=31)
    trigger_weekday: int | None = Field(None, ge=0, le=6)
    trigger_week_interval: int | None = Field(None, ge=1, le=52)
    trigger_month_day: int | None = Field(None, ge=1, le=31)
    trigger_custom_rule: str | None = Field(None, max_length=500)
    trigger_one_time_date: date | None = None
    active_days: int | None = Field(None, ge=1, le=365)
    notify_members: bool | None = None
    notification_body: str | None = Field(None, max_length=1000)
    generate_summary: bool | None = None


class PromptResponse(BaseModel):
    """@brief Full prompt object."""

    id: UUID
    title: str
    body: str
    source: str
    is_enabled: bool
    frequency_type: str
    trigger_month: int | None
    trigger_day: int | None
    trigger_weekday: int | None
    trigger_week_interval: int | None
    trigger_month_day: int | None
    trigger_custom_rule: str | None
    trigger_one_time_date: date | None
    active_days: int
    scope: str
    subgroup_id: UUID | None
    notify_members: bool
    notification_body: str | None
    linked_event_id: UUID | None
    generate_summary: bool
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromptPostResponse(BaseModel):
    """@brief A fired prompt post tracking record."""

    id: UUID
    prompt_id: UUID
    post_id: UUID
    fired_at: date
    expires_at: datetime
    response_count: int
    is_finalised: bool
    summary_post_id: UUID | None

    model_config = {"from_attributes": True}


class PromptList(BaseModel):
    """@brief Paginated prompt list."""

    items: list[PromptResponse]
    next_cursor: str | None = None
    has_more: bool = False
