"""
@file gallery.py
@brief Gallery, GalleryItem, and GalleryCollaborator models.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


class Gallery(Base):
    """@brief Named photo/video albums with access control and event linkage."""

    __tablename__ = "galleries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(),
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    cover_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL"),
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL"),
    )
    subgroup_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subgroups.id", ondelete="SET NULL"),
    )
    visibility: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="community",
    )
    contribution_policy: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="owner_only",
    )
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_event_gallery: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    search_fts = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', "
            "coalesce(title, '') || ' ' || "
            "coalesce(description, ''))",
            persisted=True,
        ),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "visibility IN ('private', 'subgroup', 'community')",
            name="galleries_visibility_ck",
        ),
        CheckConstraint(
            "contribution_policy IN ('owner_only', 'collaborators', 'community')",
            name="galleries_contribution_ck",
        ),
        Index("galleries_owner_idx", "owner_id"),
        Index("galleries_event_idx", "event_id", postgresql_where=(event_id.isnot(None))),
        Index("galleries_subgroup_idx", "subgroup_id", postgresql_where=(subgroup_id.isnot(None))),
        Index("galleries_visibility_idx", "visibility", created_at.desc()),
        Index(
            "galleries_default_user_idx", "owner_id",
            unique=True, postgresql_where=(is_default.is_(True)),
        ),
        Index(
            "galleries_event_gallery_idx", "event_id",
            unique=True, postgresql_where=(is_event_gallery.is_(True)),
        ),
        Index("galleries_search_fts_idx", "search_fts", postgresql_using="gin"),
    )


class GalleryItem(Base):
    """@brief Media items within a gallery, with ordering."""

    __tablename__ = "gallery_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(),
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
    )
    gallery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("galleries.id", ondelete="CASCADE"), nullable=False,
    )
    media_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False,
    )
    added_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False,
    )
    caption: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("gallery_id", "media_id"),
        Index("gallery_items_gallery_idx", "gallery_id", "position"),
        Index("gallery_items_media_idx", "media_id"),
    )


class GalleryCollaborator(Base):
    """@brief Users invited to contribute to a gallery."""

    __tablename__ = "gallery_collaborators"

    gallery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("galleries.id", ondelete="CASCADE"), primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True,
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
    )
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
