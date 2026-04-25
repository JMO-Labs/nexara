"""
@file gallery.py
@brief Pydantic schemas for galleries, items, and collaborators.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

GalleryVisibility = Literal["private", "subgroup", "community"]
ContributionPolicy = Literal["owner_only", "collaborators", "community"]


class GalleryCreate(BaseModel):
    """@brief Schema for creating a gallery."""

    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = Field(None, max_length=10_000)
    visibility: GalleryVisibility = "community"
    contribution_policy: ContributionPolicy = "owner_only"
    subgroup_id: UUID | None = None
    event_id: UUID | None = None
    cover_media_id: UUID | None = None


class GalleryUpdate(BaseModel):
    """@brief Schema for updating a gallery (all fields optional)."""

    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = Field(None, max_length=10_000)
    visibility: GalleryVisibility | None = None
    contribution_policy: ContributionPolicy | None = None
    cover_media_id: UUID | None = None
    is_featured: bool | None = None


class GalleryItemCreate(BaseModel):
    """@brief Schema for adding a single media item to a gallery."""

    media_id: UUID
    caption: str | None = Field(None, max_length=500)
    position: int | None = Field(None, ge=0)


class GalleryItemBulkCreate(BaseModel):
    """@brief Schema for adding multiple media items at once."""

    media_ids: list[UUID] = Field(..., min_length=1, max_length=100)


class GalleryItemUpdate(BaseModel):
    """@brief Schema for updating a gallery item."""

    caption: str | None = Field(None, max_length=500)
    position: int | None = Field(None, ge=0)


class GalleryItemResponse(BaseModel):
    """@brief A media item within a gallery."""

    id: UUID
    gallery_id: UUID
    media_id: UUID
    added_by: UUID
    caption: str | None
    position: int
    created_at: datetime

    model_config = {"from_attributes": True}


class GalleryResponse(BaseModel):
    """@brief Full gallery object."""

    id: UUID
    owner_id: UUID
    title: str
    description: str | None
    cover_media_id: UUID | None
    event_id: UUID | None
    subgroup_id: UUID | None
    visibility: str
    contribution_policy: str
    item_count: int
    is_featured: bool
    is_default: bool
    is_event_gallery: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GalleryList(BaseModel):
    """@brief Paginated gallery list."""

    items: list[GalleryResponse]
    next_cursor: str | None = None
    has_more: bool = False


class CollaboratorAdd(BaseModel):
    """@brief Schema for inviting a collaborator."""

    user_id: UUID


class CollaboratorResponse(BaseModel):
    """@brief Gallery collaborator record."""

    gallery_id: UUID
    user_id: UUID
    invited_by: UUID | None
    invited_at: datetime

    model_config = {"from_attributes": True}
