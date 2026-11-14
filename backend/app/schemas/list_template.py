"""
@file list_template.py
@brief Pydantic schemas for list templates, their fields and seed items.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ListTemplateFieldIn(BaseModel):
    """@brief Field definition supplied when creating a template."""

    key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    label: str = Field(min_length=1, max_length=128)
    type_key: str
    required: bool = False
    position: int = Field(ge=0)
    config: dict[str, Any] = Field(default_factory=dict)


class ListTemplateFieldOut(ListTemplateFieldIn):
    """@brief Persisted template field."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class ListTemplateItemIn(BaseModel):
    """@brief Seed item supplied when creating a template."""

    position: int = Field(ge=0)
    values: dict[str, Any] = Field(default_factory=dict)


class ListTemplateItemOut(ListTemplateItemIn):
    """@brief Persisted template seed item."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class ListTemplateCreate(BaseModel):
    """@brief Request body for creating a template."""

    name: str = Field(min_length=1)
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    color: str | None = None
    is_shared: bool = False
    fields: list[ListTemplateFieldIn] = Field(default_factory=list)
    items: list[ListTemplateItemIn] = Field(default_factory=list)


class ListTemplateUpdate(BaseModel):
    """@brief Partial template update; ``fields``/``items`` replace when given."""

    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    color: str | None = None
    is_shared: bool | None = None
    fields: list[ListTemplateFieldIn] | None = None
    items: list[ListTemplateItemIn] | None = None


class ListTemplateClone(BaseModel):
    """@brief Options for instantiating a template as a list."""

    title: str | None = Field(default=None, min_length=1)
    visibility: Literal["community", "subgroup", "private"] = "private"
    include_items: bool = True


class ListTemplateOut(BaseModel):
    """@brief Template response."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    category: str | None = None
    icon: str | None = None
    color: str | None = None
    cover_media_id: uuid.UUID | None = None
    is_shared: bool
    created_at: datetime
    updated_at: datetime
    fields: list[ListTemplateFieldOut] = Field(default_factory=list)
    items: list[ListTemplateItemOut] = Field(default_factory=list)


class ListTemplatePage(BaseModel):
    """@brief Page of templates."""

    templates: list[ListTemplateOut]
    cursor: str | None = None
    has_more: bool = False
