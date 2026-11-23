"""Simple mode: per-user accessibility setting.

@file 0064_simple_mode.py
@brief Add user_settings.simple_mode.

Revision ID: 0064_simple_mode
Revises: 0063_stories
"""

import sqlalchemy as sa

from alembic import op

revision = "0064_simple_mode"
down_revision = "0063_stories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Add the simple_mode column (default false)."""
    op.add_column(
        "user_settings",
        sa.Column("simple_mode", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """@brief Drop the simple_mode column."""
    op.drop_column("user_settings", "simple_mode")
