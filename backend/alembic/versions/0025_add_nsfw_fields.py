"""add is_nsfw to posts and media, mark_as_adult to user_settings

Revision ID: 0025_add_nsfw_fields
Revises: 0024_add_user_pronouns
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0025_add_nsfw_fields"
down_revision = "0024_add_user_pronouns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Add NSFW flags, partial indexes and the adult opt-in setting."""
    for table in ("posts", "media"):
        op.add_column(
            table,
            sa.Column("is_nsfw", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
        op.create_index(
            f"idx_{table}_nsfw",
            table,
            ["is_nsfw"],
            postgresql_where=sa.text("is_nsfw = true"),
        )
    op.add_column(
        "user_settings",
        sa.Column("mark_as_adult", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    """@brief Drop NSFW columns and indexes."""
    op.drop_column("user_settings", "mark_as_adult")
    for table in ("media", "posts"):
        op.drop_index(f"idx_{table}_nsfw", table_name=table)
        op.drop_column(table, "is_nsfw")
