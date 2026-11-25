"""
@file recipe.py
@brief Pydantic schemas for the recipe book.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    """@brief One ingredient line: free-text quantity and item."""

    qty: str = Field(default="", max_length=40)
    item: str = Field(min_length=1, max_length=200)


class RecipeBase(BaseModel):
    """@brief Fields shared by create and update."""

    title: str = Field(min_length=1, max_length=120)
    story: str = Field(default="", max_length=20000)
    ingredients: list[Ingredient] = Field(default_factory=list, max_length=100)
    steps: list[str] = Field(default_factory=list, max_length=60)
    servings: int | None = Field(default=None, ge=1, le=1000)
    prep_minutes: int | None = Field(default=None, ge=0, le=10000)
    cook_minutes: int | None = Field(default=None, ge=0, le=10000)
    photo_media_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)
    best_maker_user_id: uuid.UUID | None = None
    best_maker_household_id: uuid.UUID | None = None
    tags: list[str] = Field(default_factory=list, max_length=10)
    visibility: Literal["community", "subgroup", "private"] = "community"
    subgroup_id: uuid.UUID | None = None


class RecipeCreate(RecipeBase):
    """@brief Request body for creating a recipe."""


class RecipeUpdate(RecipeBase):
    """@brief Full replacement body for updating a recipe."""


class RecipeAuthor(BaseModel):
    """@brief Minimal author profile."""

    id: uuid.UUID
    display_name: str
    is_bot: bool = False


class RecipeOut(RecipeBase):
    """@brief Recipe response."""

    id: uuid.UUID
    author: RecipeAuthor
    best_maker_name: str | None = None
    created_at: datetime
    updated_at: datetime


class RecipePage(BaseModel):
    """@brief Keyset page of recipes."""

    recipes: list[RecipeOut]
    next_cursor: str | None = None


class TagCount(BaseModel):
    """@brief A tag and how many visible recipes carry it."""

    tag: str
    count: int
