"""
@file recipe_shopping.py
@brief Schemas for adding recipe ingredients to a shopping list.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ToListIn(BaseModel):
    """@brief Request: target list (None = create one) and ingredient indexes (None = all)."""

    list_id: uuid.UUID | None = None
    ingredients: list[int] | None = Field(default=None, max_length=100)


class ToListOut(BaseModel):
    """@brief Result: the list used and number of items added."""

    list_id: uuid.UUID
    added: int
