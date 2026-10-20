"""
@file branding.py
@brief CommunityBranding model — single-row table for visual customization.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


class CommunityBranding(Base):
    """
    @brief Community appearance settings: name, colors, fonts, logos.

    Single-row table — always UPSERT, never INSERT a second row.
    """

    __tablename__ = "community_branding"

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
    community_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="Nexara")
    tagline: Mapped[str | None] = mapped_column(Text)
    about_short: Mapped[str | None] = mapped_column(Text)
    logo_light_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media.id", ondelete="SET NULL"),
    )
    logo_dark_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media.id", ondelete="SET NULL"),
    )
    favicon_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media.id", ondelete="SET NULL"),
    )
    pwa_icon_192_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media.id", ondelete="SET NULL"),
    )
    pwa_icon_512_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media.id", ondelete="SET NULL"),
    )
    og_image_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media.id", ondelete="SET NULL"),
    )
    landing_hero_bg_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media.id", ondelete="SET NULL"),
    )
    color_primary: Mapped[str] = mapped_column(Text, nullable=False, server_default="#3b82f6")
    color_primary_dark: Mapped[str] = mapped_column(Text, nullable=False, server_default="#2563eb")
    color_accent: Mapped[str] = mapped_column(Text, nullable=False, server_default="#C6B4F5")
    color_surface_light: Mapped[str] = mapped_column(Text, nullable=False, server_default="#ffffff")
    color_surface_dark: Mapped[str] = mapped_column(Text, nullable=False, server_default="#1f2937")
    color_text_light: Mapped[str] = mapped_column(Text, nullable=False, server_default="#111827")
    color_text_dark: Mapped[str] = mapped_column(Text, nullable=False, server_default="#f9fafb")
    font_family: Mapped[str] = mapped_column(Text, nullable=False, server_default="Inter")
    font_family_mono: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="JetBrains Mono",
    )
    custom_css: Mapped[str | None] = mapped_column(Text)
    custom_css_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    email_logo_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media.id", ondelete="SET NULL"),
    )
    email_footer_text: Mapped[str | None] = mapped_column(Text)
    email_sender_name: Mapped[str | None] = mapped_column(Text)
    landing_cta_text: Mapped[str | None] = mapped_column(Text, server_default="Join our community")
    landing_show_feature_list: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    __table_args__ = (UniqueConstraint("community_id", name="uq_community_branding_community_id"),)
