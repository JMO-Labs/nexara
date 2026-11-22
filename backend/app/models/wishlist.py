"""
@file wishlist.py
@brief Wishlists (gift lists) for a member or one of their household
       members/pets, their items and the claims gift-givers make. Claims are
       never shown to the list's owner (keeps the surprise).
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
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
    household_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("household_members.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    occasion: Mapped[str] = mapped_column(Text, nullable=False, server_default="custom")
    occasion_date: Mapped[date | None] = mapped_column(Date)
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
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    price: Mapped[str | None] = mapped_column(Text)
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
    created_at: Mapped[datetime] = _created()
