"""
@file list.py
@brief Pydantic schemas for lists, items, signups and members.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ListVisibility = Literal["community", "subgroup", "private", "members"]


class ListCreate(BaseModel):
    """@brief Request body for creating a list."""

    title: str = Field(min_length=1)
    description: str | None = None
    visibility: ListVisibility = "community"
    subgroup_id: uuid.UUID | None = None
    field_schema: list[dict[str, Any]] = Field(default_factory=list)
    color: str | None = None


class ListUpdate(BaseModel):
    """@brief Partial update of a list."""

    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    color: str | None = None
    expires_at: datetime | None = None


class ListOut(BaseModel):
    """@brief List response."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: str | None = None
    visibility: str
    owner_id: uuid.UUID
    community_id: uuid.UUID
    template_id: uuid.UUID | None = None
    subgroup_id: uuid.UUID | None = None
    status: str
    expires_at: datetime | None = None
    color: str | None = None
    item_count: int = 0
    completed_count: int = 0
    signup_count: int = 0
    created_at: datetime
    updated_at: datetime
    field_schema: list[dict[str, Any]] = Field(default_factory=list)


class ListItemCreate(BaseModel):
    """@brief Request body for adding an item."""

    position: int = Field(ge=0)
    values: dict[str, Any] = Field(default_factory=dict)


class ListItemOut(BaseModel):
    """@brief List item response."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    position: int
    values: dict[str, Any] = Field(default_factory=dict)
    due_at: datetime | None = None
    completed: bool = False
    completed_by: uuid.UUID | None = None
    completed_at: datetime | None = None
    lat: float | None = None
    lon: float | None = None
    signup_quantity_needed: int | None = None


class SignupClaim(BaseModel):
    """@brief Request body for claiming an item."""

    quantity: int = Field(default=1, ge=1)
    note: str | None = None


class SignupOut(BaseModel):
    """@brief Signup response."""

    model_config = ConfigDict(from_attributes=True)
    item_id: uuid.UUID
    user_id: uuid.UUID
    quantity: int
    note: str | None = None
    claimed_at: datetime


class ListMemberOut(BaseModel):
    """@brief List member response."""

    model_config = ConfigDict(from_attributes=True)
    list_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    share_personal: bool
    added_at: datetime


class ListItemUpdate(BaseModel):
    """@brief Request body for updating an item's values."""

    values: dict[str, Any] = Field(default_factory=dict)


class ListMemberAdd(BaseModel):
    """@brief Request body for adding a list member."""

    user_id: uuid.UUID
    role: Literal["viewer", "editor"] = "viewer"


class Pagination(BaseModel):
    """@brief Keyset pagination metadata with an opaque cursor."""

    cursor: str | None = None
    has_more: bool = False


class ListPage(BaseModel):
    """@brief Page of lists."""

    lists: list[ListOut]
    pagination: Pagination


class ListItemPage(BaseModel):
    """@brief Page of list items."""

    items: list[ListItemOut]
    pagination: Pagination
