"""add user pronouns

Revision ID: 0022_add_user_pronouns
Revises: 0021_add_subgroup_accent_color
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0023_add_user_pronouns"
down_revision = "0022_plugin_models"
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
