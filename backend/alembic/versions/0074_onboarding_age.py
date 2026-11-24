"""Onboarding + age groups.

@file 0074_onboarding_age.py
@brief Age group columns, onboarding state, age_suggestions and NSFW columns.

Revision ID: 0074_onboarding_age
Revises: 0073_monitoring
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision = "0074_onboarding_age"
down_revision = "0073_monitoring"
branch_labels = None
depends_on = None

_GROUPS = "age_group IN ('child','teen','adult')"
_LOCKABLE = ("posts", "galleries", "media")


def upgrade() -> None:
    """@brief Add columns and age_suggestions."""
    op.add_column("users", sa.Column("age_group", sa.Text(), nullable=True))
    op.create_check_constraint("users_age_group_check", "users", _GROUPS)
    op.add_column(
        "users", sa.Column("onboarding_step", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "users", sa.Column("onboarding_done_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute("UPDATE users SET onboarding_done_at = now()")
    op.add_column("invites", sa.Column("age_group", sa.Text(), nullable=True))
    op.create_check_constraint("invites_age_group_check", "invites", _GROUPS)
    op.add_column(
        "communities",
        sa.Column("adult_requires_approval", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "communities",
        sa.Column(
            "onboarding_required",
            pg.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
    )
    op.create_table(
        "age_suggestions",
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
        ),
        sa.Column(
            "subject_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "suggested_by",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("age_group", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("decided_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(_GROUPS, name="age_suggestions_group_check"),
        sa.CheckConstraint("status IN ('pending','approved','rejected')", name="age_sugg_status"),
        sa.CheckConstraint("note IS NULL OR char_length(note) <= 500", name="age_sugg_note_len"),
    )
    op.create_index(
        "age_suggestions_pending_uq",
        "age_suggestions",
        ["subject_id", "suggested_by"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index("age_suggestions_comm_status", "age_suggestions", ["community_id", "status"])
    op.add_column(
        "galleries", sa.Column("is_nsfw", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column(
        "user_settings",
        sa.Column("always_show_nsfw", sa.Boolean(), nullable=False, server_default="false"),
    )
    # Set by a moderator: the author/owner may not clear the NSFW flag.
    for table in _LOCKABLE:
        op.add_column(
            table,
            sa.Column("nsfw_locked", sa.Boolean(), nullable=False, server_default="false"),
        )


def downgrade() -> None:
    """@brief Drop everything added by upgrade."""
    for table in _LOCKABLE:
        op.drop_column(table, "nsfw_locked")
    op.drop_column("user_settings", "always_show_nsfw")
    op.drop_column("galleries", "is_nsfw")
    op.drop_table("age_suggestions")
    op.drop_column("communities", "onboarding_required")
    op.drop_column("communities", "adult_requires_approval")
    op.drop_constraint("invites_age_group_check", "invites")
    op.drop_column("invites", "age_group")
    op.drop_column("users", "onboarding_done_at")
    op.drop_column("users", "onboarding_step")
    op.drop_constraint("users_age_group_check", "users")
    op.drop_column("users", "age_group")
