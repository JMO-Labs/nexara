"""Countdowns.

@file 0075_countdowns.py
@brief countdowns, followers, sent-reminder ledger and posts.countdown_id.

Revision ID: 0075_countdowns
Revises: 0074_onboarding_age
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision = "0075_countdowns"
down_revision = "0074_onboarding_age"
branch_labels = None
depends_on = None

_COMMUNITY = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    """@brief Create countdown tables and the posts link."""
    op.create_table(
        "countdowns",
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "community_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
            server_default=_COMMUNITY,
        ),
        sa.Column(
            "author_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("target_time", sa.Time(), nullable=True),
        sa.Column("tz", sa.Text(), nullable=False, server_default="UTC"),
        sa.Column("emoji", sa.Text(), nullable=True),
        sa.Column(
            "cover_media_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("media.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("repeat_yearly", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("visibility", sa.Text(), nullable=False, server_default="community"),
        sa.Column(
            "subgroup_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("subgroups.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("post_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("char_length(title) <= 120", name="countdowns_title_len"),
        sa.CheckConstraint("emoji IS NULL OR char_length(emoji) <= 8", name="countdowns_emoji_len"),
        sa.CheckConstraint(
            "visibility IN ('community','subgroup','private')", name="countdowns_visibility_check"
        ),
    )
    op.create_index("countdowns_community_date_idx", "countdowns", ["community_id", "target_date"])
    op.create_table(
        "countdown_followers",
        sa.Column(
            "countdown_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("countdowns.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "countdown_reminders_sent",
        sa.Column(
            "countdown_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("countdowns.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("kind", sa.Text(), primary_key=True),
        sa.Column("occurrence", sa.Date(), primary_key=True),
        sa.CheckConstraint("kind IN ('d7','d1','d0')", name="countdown_reminders_kind_check"),
    )
    for ch, default in (("inapp", "true"), ("push", "true"), ("email", "false")):
        op.add_column(
            "user_settings",
            sa.Column(
                f"notif_countdown_reminder_{ch}",
                sa.Boolean(),
                nullable=False,
                server_default=default,
            ),
        )
    op.add_column(
        "posts",
        sa.Column(
            "countdown_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("countdowns.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """@brief Drop countdown tables and the posts link."""
    op.drop_column("posts", "countdown_id")
    for ch in ("inapp", "push", "email"):
        op.drop_column("user_settings", f"notif_countdown_reminder_{ch}")
    op.drop_table("countdown_reminders_sent")
    op.drop_table("countdown_followers")
    op.drop_index("countdowns_community_date_idx", table_name="countdowns")
    op.drop_table("countdowns")
