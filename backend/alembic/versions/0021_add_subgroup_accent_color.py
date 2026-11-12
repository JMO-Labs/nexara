"""add subgroup accent_color

Revision ID: 0021_add_subgroup_accent_color
Revises: 0020_media_ai_metadata
"""

import sqlalchemy as sa

from alembic import op

revision = "0021_add_subgroup_accent_color"
down_revision = "0020_media_ai_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Add nullable accent_color and partial index."""
    op.add_column("subgroups", sa.Column("accent_color", sa.Text(), nullable=True))
    op.create_index(
        "idx_subgroups_accent_color",
        "subgroups",
        ["accent_color"],
        postgresql_where=sa.text("accent_color IS NOT NULL"),
    )


def downgrade() -> None:
    """@brief Drop index and column."""
    op.drop_index("idx_subgroups_accent_color", table_name="subgroups")
    op.drop_column("subgroups", "accent_color")
