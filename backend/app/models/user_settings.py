"""
@file user_settings.py
@brief Per-user preferences: notifications, privacy, appearance, locale.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, MappedColumn, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


def _bool_col(default: str = "true") -> MappedColumn[bool]:
    """@brief Shorthand for a non-nullable Boolean column with a server default."""
    return mapped_column(Boolean, nullable=False, server_default=default)


class UserSettings(Base):
    """
    @brief One-to-one companion to User storing all preference columns.

    Created with defaults on user registration (UPSERT pattern).
    """

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
    )

    # --- Notification preferences v2: {type_key: {channel: bool}} ---
    # Legacy notif_* / mute_all_* columns below are still the source of truth for
    # readers; migration b2c3d4e5f6a7 only backfills prefs. Dropped in a follow-up.
    notification_prefs: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    dnd_schedule: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    dnd_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dnd_timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default="UTC")
    digest_cadence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    digest_last_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- Legacy notification preferences (type x channel) ---
    notif_mention_inapp: Mapped[bool] = _bool_col()
    notif_mention_push: Mapped[bool] = _bool_col()
    notif_mention_email: Mapped[bool] = _bool_col()
    notif_comment_inapp: Mapped[bool] = _bool_col()
    notif_comment_push: Mapped[bool] = _bool_col()
    notif_comment_email: Mapped[bool] = _bool_col()
    notif_reaction_inapp: Mapped[bool] = _bool_col()
    notif_reaction_push: Mapped[bool] = _bool_col()
    notif_reaction_email: Mapped[bool] = _bool_col("false")
    notif_new_post_inapp: Mapped[bool] = _bool_col()
    notif_new_post_push: Mapped[bool] = _bool_col("false")
    notif_new_post_email: Mapped[bool] = _bool_col("false")
    notif_event_reminder_inapp: Mapped[bool] = _bool_col()
    notif_event_reminder_push: Mapped[bool] = _bool_col()
    notif_event_reminder_email: Mapped[bool] = _bool_col()
    notif_event_rsvp_inapp: Mapped[bool] = _bool_col()
    notif_event_rsvp_push: Mapped[bool] = _bool_col("false")
    notif_event_rsvp_email: Mapped[bool] = _bool_col("false")
    notif_gallery_activity_inapp: Mapped[bool] = _bool_col()
    notif_gallery_activity_push: Mapped[bool] = _bool_col("false")
    notif_gallery_activity_email: Mapped[bool] = _bool_col("false")
    notif_dm_inapp: Mapped[bool] = _bool_col()
    notif_dm_push: Mapped[bool] = _bool_col()
    notif_dm_email: Mapped[bool] = _bool_col()
    notif_prompt_inapp: Mapped[bool] = _bool_col()
    notif_prompt_push: Mapped[bool] = _bool_col()
    notif_prompt_email: Mapped[bool] = _bool_col("false")
    notif_prompt_summary_inapp: Mapped[bool] = _bool_col()
    notif_prompt_summary_push: Mapped[bool] = _bool_col("false")
    notif_prompt_summary_email: Mapped[bool] = _bool_col("false")
    notif_list_item_inapp: Mapped[bool] = _bool_col()
    notif_list_item_email: Mapped[bool] = _bool_col("false")
    notif_list_signup_inapp: Mapped[bool] = _bool_col()
    notif_list_signup_email: Mapped[bool] = _bool_col("false")
    notif_list_completed_inapp: Mapped[bool] = _bool_col()
    notif_list_completed_email: Mapped[bool] = _bool_col("false")
    notif_list_expiring_inapp: Mapped[bool] = _bool_col()
    notif_list_expiring_email: Mapped[bool] = _bool_col("false")
    notif_list_member_inapp: Mapped[bool] = _bool_col()
    notif_list_member_email: Mapped[bool] = _bool_col("false")
    notif_birthday_inapp: Mapped[bool] = _bool_col()
    notif_birthday_push: Mapped[bool] = _bool_col("false")
    notif_birthday_email: Mapped[bool] = _bool_col("false")
    notif_system_inapp: Mapped[bool] = _bool_col()
    notif_system_push: Mapped[bool] = _bool_col()
    notif_system_email: Mapped[bool] = _bool_col()
    notif_poll_inapp: Mapped[bool] = _bool_col()
    notif_poll_push: Mapped[bool] = _bool_col("false")
    notif_poll_email: Mapped[bool] = _bool_col("false")
    notif_invite_accepted_inapp: Mapped[bool] = _bool_col()
    notif_invite_accepted_push: Mapped[bool] = _bool_col()
    notif_invite_accepted_email: Mapped[bool] = _bool_col("false")
    notif_nudge_inapp: Mapped[bool] = _bool_col()
    notif_nudge_push: Mapped[bool] = _bool_col("false")
    notif_nudge_email: Mapped[bool] = _bool_col("false")
    receive_gentle_nudges: Mapped[bool] = _bool_col()

    # Email digest
    email_digest_enabled: Mapped[bool] = _bool_col("false")
    email_digest_hour: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="8")

    # Global mute
    mute_all_push: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    mute_all_email: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    # Privacy
    profile_visible_to: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="community",
    )
    show_online_status: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    show_last_seen: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    show_birthday_year: Mapped[bool] = _bool_col("false")
    show_birthday_to: Mapped[str] = mapped_column(Text, nullable=False, server_default="community")
    mark_as_adult: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    allow_sassybot: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    # Appearance
    theme: Mapped[str] = mapped_column(Text, nullable=False, server_default="system")
    font_size: Mapped[str] = mapped_column(Text, nullable=False, server_default="medium")
    compact_feed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    # Locale
    locale: Mapped[str] = mapped_column(Text, nullable=False, server_default="en-US")

    # Home page layout — arbitrary JSON blob; None means "use default"
    home_layout: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=None)

    # Timestamps
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
