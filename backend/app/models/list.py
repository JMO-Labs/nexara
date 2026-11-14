"""
@file list.py
@brief List models: List, ListMember, ListItem, ListItemSignup, ListItemCompletion.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class List(Base):
    """
    @brief A community list instantiated from a template (or from scratch).
    """

    __tablename__ = "list"
    __table_args__ = (
        CheckConstraint(
            "visibility IN ('community','subgroup','private','members')", name="ck_list_visibility"
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("list_template.id", ondelete="SET NULL")
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(Text, nullable=False)
    subgroup_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subgroups.id", ondelete="SET NULL")
    )
    cover_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    field_schema: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    signup_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _now()
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    search_fts = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,''))",
            persisted=True,
        ),
    )

    items: Mapped[list[ListItem]] = relationship(
        back_populates="list_obj", cascade="all, delete-orphan", order_by="ListItem.position"
    )
    members: Mapped[list[ListMember]] = relationship(
        back_populates="list_obj", cascade="all, delete-orphan"
    )


class ListMember(Base):
    """
    @brief Explicit list membership with role (PK: list_id, user_id).
    """

    __tablename__ = "list_member"

    list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("list.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default="viewer")
    share_personal: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    list_obj: Mapped[List] = relationship(back_populates="members")


class ListItem(Base):
    """
    @brief A row in a list; field data lives in the JSONB values column.
    """

    __tablename__ = "list_item"

    id: Mapped[uuid.UUID] = _uuid_pk()
    list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("list.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    values: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    signup_quantity_needed: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _now()
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    list_obj: Mapped[List] = relationship(back_populates="items")
    signups: Mapped[list[ListItemSignup]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    completions: Mapped[list[ListItemCompletion]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class ListItemSignup(Base):
    """
    @brief A user's claim on an item (PK: item_id, user_id).
    """

    __tablename__ = "list_item_signup"

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("list_item.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    note: Mapped[str | None] = mapped_column(Text)
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    item: Mapped[ListItem] = relationship(back_populates="signups")


class ListItemCompletion(Base):
    """
    @brief Per-user completion of an item (PK: item_id, user_id).
    """

    __tablename__ = "list_item_completion"

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("list_item.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    item: Mapped[ListItem] = relationship(back_populates="completions")
