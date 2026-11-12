"""add user pronouns

Revision ID: 0024_add_user_pronouns
Revises: 0023_bookmarks
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0024_add_user_pronouns"
down_revision = "0023_bookmarks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Add nullable pronouns column and partial index."""
    op.add_column("users", sa.Column("pronouns", sa.Text(), nullable=True))
    op.create_index(
        "idx_users_pronouns",
        "users",
        ["pronouns"],
        postgresql_where=sa.text("pronouns IS NOT NULL"),
    )


def downgrade() -> None:
    """@brief Drop pronouns index and column."""
    op.drop_index("idx_users_pronouns", table_name="users")
    op.drop_column("users", "pronouns")
