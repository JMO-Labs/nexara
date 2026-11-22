"""
@file wishlist.py
@brief Wishlist request/response models. Money is integer cents in the
       list's currency. Claim fields are null for viewers who may not see
       claims (the owner and member recipients when ``hide_claims``).
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.profile import Level

OCCASIONS = (
    "birthday",
    "baby_shower",
    "wedding",
    "bridal_shower",
    "anniversary",
    "graduation",
    "retirement",
    "housewarming",
    "holiday",
    "back_to_school",
    "reunion",
    "party",
    "get_well",
    "farewell",
    "custom",
)
Occasion = Literal[
    "birthday",
    "baby_shower",
    "wedding",
    "bridal_shower",
    "anniversary",
    "graduation",
    "retirement",
    "housewarming",
    "holiday",
    "back_to_school",
    "reunion",
    "party",
    "get_well",
    "farewell",
    "custom",
]
RecipientKind = Literal["user", "household", "subgroup", "name", "everyone"]
Cents = int | None


def _blank_none(v: str | None) -> str | None:
    """@brief Trim; empty becomes None."""
    if v is None:
        return None
    v = v.strip()
    return v or None


def _http(v: str | None) -> str | None:
    """@brief Links must be http(s) (never javascript:, data:, ...)."""
    if v is not None and not v.lower().startswith(("http://", "https://")):
        raise ValueError("Link must start with http:// or https://")
    return v


class RecipientIn(BaseModel):
    """@brief One recipient: a member, household member, group, typed name or everyone."""

    kind: RecipientKind
    ref_id: uuid.UUID | None = None
    name: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def _shape(self) -> RecipientIn:
        self.name = _blank_none(self.name)
        if self.kind == "name" and not self.name:
            raise ValueError("A typed recipient needs a name")
        if self.kind in ("user", "household", "subgroup") and self.ref_id is None:
            raise ValueError("Pick who the list is for")
        return self


class RegistryLink(BaseModel):
    """@brief A registry elsewhere (Amazon, Target, Zola, ...)."""

    label: str = Field(min_length=1, max_length=60)
    url: str = Field(max_length=500)

    @field_validator("url")
    @classmethod
    def _url(cls, v: str) -> str:
        return _http(v.strip()) or ""


class _ListFields(BaseModel):
    """@brief Fields shared by create and update."""

    occasion_label: str | None = Field(default=None, max_length=60)
    event_date: date | None = None
    due_by: date | None = None
    note: str | None = Field(default=None, max_length=1000)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    budget_min_cents: Cents = Field(default=None, ge=0, le=100_000_00)
    budget_max_cents: Cents = Field(default=None, ge=0, le=100_000_00)
    event_budget_cents: Cents = Field(default=None, ge=0, le=10_000_000_00)
    giver_cap_cents: Cents = Field(default=None, ge=0, le=100_000_00)
    hide_claims: bool | None = None
    registry_links: list[RegistryLink] | None = Field(default=None, max_length=10)
    recipients: list[RecipientIn] | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def _ranges(self) -> _ListFields:
        self.occasion_label = _blank_none(self.occasion_label)
        lo, hi = self.budget_min_cents, self.budget_max_cents
        if lo is not None and hi is not None and lo > hi:
            raise ValueError("Budget minimum is above the maximum")
        if self.due_by and self.event_date and self.due_by > self.event_date:
            raise ValueError("Due-by date is after the event")
        return self


class WishlistCreate(_ListFields):
    """@brief New wishlist (no recipients means it's for you)."""

    title: str = Field(min_length=1, max_length=120)
    occasion: Occasion = "custom"
    visibility: Level = "groups"


class WishlistUpdate(_ListFields):
    """@brief Partial update; omitted fields are untouched."""

    title: str | None = Field(default=None, min_length=1, max_length=120)
    occasion: Occasion | None = None
    visibility: Level | None = None


class ItemIn(BaseModel):
    """@brief A gift (price, quantity) or a cash fund (goal)."""

    kind: Literal["gift", "fund"] = "gift"
    name: str = Field(min_length=1, max_length=200)
    url: str | None = Field(default=None, max_length=500)
    price_cents: Cents = Field(default=None, ge=0, le=100_000_00)
    goal_cents: Cents = Field(default=None, ge=100, le=10_000_000_00)
    notes: str | None = Field(default=None, max_length=500)
    qty: int = Field(default=1, ge=1, le=99)

    @field_validator("url", "notes")
    @classmethod
    def _trim(cls, v: str | None) -> str | None:
        return _blank_none(v)

    @field_validator("url")
    @classmethod
    def _link(cls, v: str | None) -> str | None:
        return _http(v)

    @model_validator(mode="after")
    def _fund(self) -> ItemIn:
        if self.kind == "fund":
            if self.goal_cents is None:
                raise ValueError("A fund needs a goal")
            self.qty, self.price_cents = 1, None
        else:
            self.goal_cents = None
        return self


class ItemUpdate(BaseModel):
    """@brief Partial item update (kind can't change)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    url: str | None = Field(default=None, max_length=500)
    price_cents: Cents = Field(default=None, ge=0, le=100_000_00)
    goal_cents: Cents = Field(default=None, ge=100, le=10_000_000_00)
    notes: str | None = Field(default=None, max_length=500)
    qty: int | None = Field(default=None, ge=1, le=99)

    @field_validator("url", "notes")
    @classmethod
    def _trim(cls, v: str | None) -> str | None:
        return _blank_none(v)

    @field_validator("url")
    @classmethod
    def _link(cls, v: str | None) -> str | None:
        return _http(v)


class ClaimIn(BaseModel):
    """@brief Gifts: how many you'll give. Funds: how much you'll put in."""

    qty: int = Field(default=1, ge=1, le=99)
    amount_cents: Cents = Field(default=None, ge=100, le=10_000_000_00)


class RecipientOut(BaseModel):
    """@brief Recipient with a display name."""

    kind: RecipientKind
    ref_id: uuid.UUID | None = None
    name: str
    extra: str | None = None  # household kind ("pet") or group slug


class Claimer(BaseModel):
    """@brief Who claimed (only when claims are visible to the viewer)."""

    user_id: uuid.UUID
    name: str
    qty: int
    amount_cents: int | None = None


class Preview(BaseModel):
    """@brief Shopping link preview (image served by the preview proxy)."""

    id: uuid.UUID
    title: str | None = None
    site_name: str | None = None
    has_image: bool = False


class ItemOut(BaseModel):
    """@brief An item; ``claimed``/``mine`` are null when claims are hidden from you."""

    id: uuid.UUID
    kind: Literal["gift", "fund"]
    name: str
    url: str | None = None
    price_cents: int | None = None
    goal_cents: int | None = None
    notes: str | None = None
    qty: int
    claimed: int | None = None
    mine: int | None = None
    claimers: list[Claimer] | None = None
    preview: Preview | None = None


class WishlistOut(BaseModel):
    """@brief Wishlist summary (cards)."""

    id: uuid.UUID
    owner_id: uuid.UUID
    owner_name: str = ""
    title: str
    occasion: Occasion
    occasion_label: str | None = None
    event_date: date | None = None
    due_by: date | None = None
    note: str | None = None
    visibility: Level
    currency: str = "USD"
    budget_min_cents: int | None = None
    budget_max_cents: int | None = None
    event_budget_cents: int | None = None
    giver_cap_cents: int | None = None
    hide_claims: bool = True
    registry_links: list[RegistryLink] = Field(default_factory=list)
    recipients: list[RecipientOut] = Field(default_factory=list)
    item_count: int = 0
    is_owner: bool = False
    can_edit_items: bool = False
    sees_claims: bool = False


class WishlistDetail(WishlistOut):
    """@brief Wishlist with items, plus planning totals for managers."""

    items: list[ItemOut] = Field(default_factory=list)
    planned_cents: int | None = None
    my_total_cents: int = 0
