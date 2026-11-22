"""
@file wishlist.py
@brief Wishlists (gift and event lists) for anyone: members, household
       members/pets, groups, typed names or everyone; their items (gifts or
       cash funds) and the claims givers make. With ``hide_claims`` the owner
       and member recipients never see claims (keeps the surprise).
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


def _id() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )


def _community() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
    )


def _created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Wishlist(Base):
    """@brief Row in wishlists (migration 0041)."""

    __tablename__ = "wishlists"

    id: Mapped[uuid.UUID] = _id()
    community_id: Mapped[uuid.UUID] = _community()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    occasion: Mapped[str] = mapped_column(Text, nullable=False, server_default="custom")
    occasion_label: Mapped[str | None] = mapped_column(Text)
    event_date: Mapped[date | None] = mapped_column(Date)
    due_by: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(Text, nullable=False, server_default="USD")
    budget_min_cents: Mapped[int | None] = mapped_column(Integer)
    budget_max_cents: Mapped[int | None] = mapped_column(Integer)
    event_budget_cents: Mapped[int | None] = mapped_column(Integer)
    giver_cap_cents: Mapped[int | None] = mapped_column(Integer)
    hide_claims: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    registry_links: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    note: Mapped[str | None] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(Text, nullable=False, server_default="groups")
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WishlistItem(Base):
    """@brief Row in wishlist_items."""

    __tablename__ = "wishlist_items"

    id: Mapped[uuid.UUID] = _id()
    community_id: Mapped[uuid.UUID] = _community()
    wishlist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wishlists.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False, server_default="gift")
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    price_cents: Mapped[int | None] = mapped_column(Integer)
    goal_cents: Mapped[int | None] = mapped_column(Integer)
    # The price follows the shop (filled from the link and refreshed) until
    # someone types their own.
    price_auto: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    preview_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("link_previews.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    qty: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = _created()
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WishlistClaim(Base):
    """@brief Row in wishlist_claims: someone will give ``qty`` of an item."""

    __tablename__ = "wishlist_claims"

    id: Mapped[uuid.UUID] = _id()
    community_id: Mapped[uuid.UUID] = _community()
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wishlist_items.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    qty: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    amount_cents: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = _created()


class WishlistRecipient(Base):
    """@brief Who a wishlist is for: user, household, subgroup, a typed name, or everyone."""

    __tablename__ = "wishlist_recipients"

    id: Mapped[uuid.UUID] = _id()
    community_id: Mapped[uuid.UUID] = _community()
    wishlist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wishlists.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    name: Mapped[str | None] = mapped_column(Text)
