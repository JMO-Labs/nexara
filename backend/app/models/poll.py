"""
@file poll.py
@brief Poll, PollOption, and PollVote models for community polls.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.user import COMMUNITY_DEFAULT


class Poll(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    @brief Community poll with question, options, and voting.

    Supports single/multiple/yes_no/photo types. Can be attached to a post
    or standalone. Soft-deleted via deleted_at.
    """

    __tablename__ = "polls"

    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
    )
    post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    poll_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="single",
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    allow_add_options: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("polls_community_idx", "community_id"),
        Index("polls_post_idx", "post_id"),
    )


class PollOption(Base, UUIDPrimaryKeyMixin):
    """
    @brief A single choice option within a poll.

    Optionally has an image. Position controls display order.
    """

    __tablename__ = "poll_options"

    poll_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("polls.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    image_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media.id", ondelete="SET NULL"),
        nullable=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class PollVote(Base, UUIDPrimaryKeyMixin):
    """
    @brief A user's vote for a specific poll option.

    One vote per user per option per poll. UniqueConstraint enforces this.
    """

    __tablename__ = "poll_votes"

    poll_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("polls.id", ondelete="CASCADE"),
        nullable=False,
    )
    option_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("poll_options.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "poll_id",
            "option_id",
            "user_id",
            name="uq_poll_vote_poll_option_user",
        ),
    )
