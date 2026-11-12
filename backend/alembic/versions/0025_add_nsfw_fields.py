"""add is_nsfw to posts and media

Revision ID: 0025_add_nsfw_fields
Revises: b2c3d4e5f6a7
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0025_add_nsfw_fields"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None

_TABLES = (("posts", "idx_posts_nsfw"), ("media", "idx_media_nsfw"))


def upgrade() -> None:
    """@brief Add is_nsfw columns with partial indexes on flagged rows."""
    for table, index in _TABLES:
        op.add_column(
            table,
            sa.Column("is_nsfw", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.create_index(index, table, ["is_nsfw"], postgresql_where=sa.text("is_nsfw = true"))


def downgrade() -> None:
    """@brief Drop indexes and is_nsfw columns."""
    for table, index in reversed(_TABLES):
        op.drop_index(index, table_name=table)
        op.drop_column(table, "is_nsfw")
