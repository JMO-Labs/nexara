"""Time capsules and their recipients.

@file 0052_time_capsules.py
@brief Add time_capsules and time_capsule_recipients.

Revision ID: 0052_time_capsules
Revises: 0050_features_tz
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0052_time_capsules"
down_revision = "0050_features_tz"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Create both tables and the open-due index."""
    op.create_table(
        "time_capsules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "community_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
            server_default=sa.text("'00000000-0000-0000-0000-000000000001'::uuid"),
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "media_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column("open_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("char_length(title) <= 120", name="time_capsules_title_ck"),
    )
    op.create_index(
        "ix_time_capsules_due",
        "time_capsules",
        ["open_at"],
        postgresql_where=sa.text("opened_at IS NULL AND deleted_at IS NULL"),
    )
    op.create_index("ix_time_capsules_author", "time_capsules", ["author_id"])
    op.create_table(
        "time_capsule_recipients",
        sa.Column(
            "capsule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("time_capsules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        # community kind stores the community id here (PK columns cannot be NULL).
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("capsule_id", "kind", "target_id"),
        sa.CheckConstraint(
            "kind IN ('user','subgroup','community','household')",
            name="time_capsule_recipients_kind_ck",
        ),
    )


def downgrade() -> None:
    """@brief Drop both tables."""
    op.drop_table("time_capsule_recipients")
    op.drop_index("ix_time_capsules_author", table_name="time_capsules")
    op.drop_index("ix_time_capsules_due", table_name="time_capsules")
    op.drop_table("time_capsules")
