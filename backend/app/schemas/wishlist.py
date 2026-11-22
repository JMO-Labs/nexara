"""
@file wishlist.py
@brief Wishlist request/response models. Claim fields are null for the
       owner so the surprise is kept.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.profile import Level

Occasion = Literal["birthday", "holiday", "school", "wedding", "baby", "custom"]


def _blank_none(v: str | None) -> str | None:
    """@brief Trim; empty becomes None."""
    if v is None:
        return None
    v = v.strip()
    return v or None


class WishlistCreate(BaseModel):
    """@brief New wishlist, for yourself or a household member/pet you manage."""

    title: str = Field(min_length=1, max_length=120)
    occasion: Occasion = "custom"
    occasion_date: date | None = None
    note: str | None = Field(default=None, max_length=500)
    visibility: Level = "groups"
    household_id: uuid.UUID | None = None


class WishlistUpdate(BaseModel):
    """@brief Partial update; omitted fields are untouched."""

    title: str | None = Field(default=None, min_length=1, max_length=120)
    occasion: Occasion | None = None
    occasion_date: date | None = None
    note: str | None = Field(default=None, max_length=500)
    visibility: Level | None = None


class ItemIn(BaseModel):
    """@brief A wish: what, where to find it, rough price, how many."""

    name: str = Field(min_length=1, max_length=200)
    url: str | None = Field(default=None, max_length=500)
    price: str | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=500)
    qty: int = Field(default=1, ge=1, le=99)

    @field_validator("url", "price", "notes")
    @classmethod
    def _trim(cls, v: str | None) -> str | None:
        return _blank_none(v)

    @field_validator("url")
    @classmethod
    def _http(cls, v: str | None) -> str | None:
        """@brief Links must be http(s) (never javascript:, data:, ...)."""
        if v is not None and not v.lower().startswith(("http://", "https://")):
            raise ValueError("Link must start with http:// or https://")
        return v


class ItemUpdate(ItemIn):
    """@brief Partial item update."""

    name: str | None = Field(default=None, min_length=1, max_length=200)  # type: ignore[assignment]
    qty: int | None = Field(default=None, ge=1, le=99)  # type: ignore[assignment]


class ClaimIn(BaseModel):
    """@brief How many of an item you will give."""

    qty: int = Field(default=1, ge=1, le=99)


class HouseholdBrief(BaseModel):
    """@brief Who a household wishlist is for."""

    id: uuid.UUID
    name: str
    kind: str


class ItemOut(BaseModel):
    """@brief An item; ``claimed``/``mine`` are null for the owner."""

    id: uuid.UUID
    name: str
    url: str | None = None
    price: str | None = None
    notes: str | None = None
    qty: int
    claimed: int | None = None
    mine: int | None = None


class WishlistOut(BaseModel):
    """@brief Wishlist summary (cards)."""

    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    occasion: Occasion
    occasion_date: date | None = None
    note: str | None = None
    visibility: Level
    household: HouseholdBrief | None = None
    item_count: int = 0
    is_owner: bool = False


class WishlistDetail(WishlistOut):
    """@brief Wishlist with its items."""

    items: list[ItemOut] = Field(default_factory=list)
