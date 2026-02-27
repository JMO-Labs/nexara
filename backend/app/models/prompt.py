"""
@file prompt.py
@brief Tradition prompt models: Prompt and PromptPost.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


class Prompt(Base):
    """@brief Tradition prompts — scheduled community engagement posts."""

    __tablename__ = "prompts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="builtin")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    frequency_type: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_month: Mapped[int | None] = mapped_column(SmallInteger)
    trigger_day: Mapped[int | None] = mapped_column(SmallInteger)
    trigger_weekday: Mapped[int | None] = mapped_column(SmallInteger)
    trigger_week_interval: Mapped[int | None] = mapped_column(SmallInteger)
    trigger_month_day: Mapped[int | None] = mapped_column(SmallInteger)
    trigger_custom_rule: Mapped[str | None] = mapped_column(Text)
    trigger_one_time_date: Mapped[date | None] = mapped_column(Date)
    active_days: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="7")
    scope: Mapped[str] = mapped_column(Text, nullable=False, server_default="community")
    subgroup_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subgroups.id", ondelete="CASCADE"),
    )
    notify_members: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    notification_body: Mapped[str | None] = mapped_column(Text)
    linked_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
    )
    generate_summary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("prompts_enabled_idx", "is_enabled", postgresql_where=(is_enabled.is_(True))),
    )


class PromptPost(Base):
    """@brief Links a fired prompt to its pinned feed post."""

    __tablename__ = "prompt_posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
    )
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="CASCADE"),
        nullable=False,
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    fired_at: Mapped[date] = mapped_column(Date, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    response_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_finalised: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    summary_post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="SET NULL"),
    )

    __table_args__ = (UniqueConstraint("prompt_id", "fired_at"),)
