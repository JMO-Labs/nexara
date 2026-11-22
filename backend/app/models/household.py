"""
@file household.py
@brief Household member without an account: a child, relative or pet the
       owner manages. Visibility uses the profile levels (private, groups,
       community); the pet care card has its own level.
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


class HouseholdMember(Base):
    """@brief Row in household_members (migration 0037)."""

    __tablename__ = "household_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    relation: Mapped[str | None] = mapped_column(Text)
    birthday: Mapped[date | None] = mapped_column(Date)
    show_birth_year: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    photo_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL")
    )
    visibility: Mapped[str] = mapped_column(Text, nullable=False, server_default="groups")
    bio: Mapped[str | None] = mapped_column(Text)
    species: Mapped[str | None] = mapped_column(Text)
    breed: Mapped[str | None] = mapped_column(Text)
    gotcha_day: Mapped[date | None] = mapped_column(Date)
    likes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    dislikes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    care_card: Mapped[str | None] = mapped_column(Text)
    care_visibility: Mapped[str] = mapped_column(Text, nullable=False, server_default="private")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
