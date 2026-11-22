"""
@file recipe.py
@brief Family recipe book row (migration 0055).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Computed, DateTime, ForeignKey, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


class Recipe(Base):
    """@brief Row in recipes. ``visibility`` is community, subgroup or private."""

    __tablename__ = "recipes"

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
    story: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    ingredients: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    steps: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    servings: Mapped[int | None] = mapped_column(Integer)
    prep_minutes: Mapped[int | None] = mapped_column(Integer)
    cook_minutes: Mapped[int | None] = mapped_column(Integer)
    photo_media_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, server_default="{}"
    )
    best_maker_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    best_maker_household_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("household_members.id", ondelete="SET NULL")
    )
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    visibility: Mapped[str] = mapped_column(Text, nullable=False, server_default="community")
    subgroup_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subgroups.id", ondelete="SET NULL")
    )
    search_fts = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', coalesce(title,'') || ' ' || coalesce(story,'')"
            " || ' ' || coalesce(ingredients::text,''))",
            persisted=True,
        ),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
