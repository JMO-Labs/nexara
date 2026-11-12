"""
@file models.py
@brief Pydantic schemas for recipes (persisted as JSON in plugin_data, no extra tables).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Ingredient(BaseModel):
    """@brief One ingredient line."""

    name: str = Field(min_length=1, max_length=200)
    qty: float | None = None
    unit: str = Field(default="", max_length=30)


class RecipeIn(BaseModel):
    """@brief Create/update payload."""

    name: str = Field(min_length=1, max_length=200)
    ingredients: list[Ingredient] = Field(default_factory=list, max_length=100)
    steps: list[str] = Field(default_factory=list, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=20)
    image_url: str | None = Field(default=None, max_length=2048)

    @field_validator("tags")
    @classmethod
    def _norm_tags(cls, v: list[str]) -> list[str]:
        return sorted({t.strip().lower() for t in v if t.strip()})
