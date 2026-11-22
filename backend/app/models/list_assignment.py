"""
@file list_assignment.py
@brief Models for list item assignments and the per-list activity log.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

COMMUNITY_DEFAULT = text("'00000000-0000-0000-0000-000000000001'::uuid")
ACTIVE_STATUSES = ("pending", "accepted")


def _pk() -> Mapped[uuid.UUID]:
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


class ListItemAssignment(Base):
    """@brief Who is assigned to (or took) a list item; one active row per item."""

    __tablename__ = "list_item_assignments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','accepted','declined')", name="ck_list_item_assignment_status"
        ),
        Index(
            "uq_list_item_assignment_active",
            "item_id",
            unique=True,
            postgresql_where=text("status IN ('pending','accepted')"),
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    community_id: Mapped[uuid.UUID] = _community()
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("list_item.id", ondelete="CASCADE"), nullable=False
    )
    list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("list.id", ondelete="CASCADE"), nullable=False
    )
    assignee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    assigned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ListActivity(Base):
    """@brief Append-only log entry of an action on a list."""

    __tablename__ = "list_activity"
    __table_args__ = (Index("ix_list_activity_list_created", "list_id", text("created_at DESC")),)

    id: Mapped[uuid.UUID] = _pk()
    community_id: Mapped[uuid.UUID] = _community()
    list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("list.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    item_title: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
