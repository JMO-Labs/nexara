"""
@file countdown.py
@brief Countdown, follower and sent-reminder models.
"""

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


class Countdown(Base):
    """@brief A dated countdown (optionally yearly) shared with a scope."""

    __tablename__ = "countdowns"
    __table_args__ = (
        CheckConstraint("char_length(title) <= 120", name="countdowns_title_len"),
        CheckConstraint("emoji IS NULL OR char_length(emoji) <= 8", name="countdowns_emoji_len"),
        CheckConstraint(
            "visibility IN ('community','subgroup','private')", name="countdowns_visibility_check"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_time: Mapped[time | None] = mapped_column(Time)
    tz: Mapped[str] = mapped_column(Text, nullable=False, server_default="UTC")
    emoji: Mapped[str | None] = mapped_column(Text)
    cover_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL")
    )
    repeat_yearly: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    visibility: Mapped[str] = mapped_column(Text, nullable=False, server_default="community")
    subgroup_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subgroups.id", ondelete="SET NULL")
    )
    post_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CountdownFollower(Base):
    """@brief A member following a countdown (gets reminders, shows on Home)."""

    __tablename__ = "countdown_followers"

    countdown_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("countdowns.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CountdownReminderSent(Base):
    """@brief Ledger making reminders idempotent per user/kind/occurrence."""

    __tablename__ = "countdown_reminders_sent"
    __table_args__ = (
        CheckConstraint("kind IN ('d7','d1','d0')", name="countdown_reminders_kind_check"),
    )

    countdown_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("countdowns.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(Text, primary_key=True)
    occurrence: Mapped[date] = mapped_column(Date, primary_key=True)
