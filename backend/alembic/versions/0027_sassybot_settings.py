"""add sassybot settings to communities

Revision ID: 0027_sassybot_settings
Revises: 0026_list_templates
Create Date: 2026-11-12 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "0027_sassybot_settings"
down_revision = "0026_list_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Add Sassybot configuration columns to communities."""
    op.add_column(
        "communities",
        sa.Column("sassybot_enabled", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "communities",
        sa.Column("sassybot_sass_level", sa.Integer(), server_default="2", nullable=False),
    )
    op.add_column(
        "communities",
        sa.Column("sassybot_probability", sa.Integer(), server_default="15", nullable=False),
    )
    op.add_column(
        "communities",
        sa.Column("sassybot_invoke_only", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_check_constraint(
        "communities_sassybot_sass_chk", "communities", "sassybot_sass_level BETWEEN 1 AND 3"
    )
    op.create_check_constraint(
        "communities_sassybot_prob_chk", "communities", "sassybot_probability BETWEEN 0 AND 100"
    )


def downgrade() -> None:
    """@brief Drop Sassybot configuration columns."""
    op.drop_constraint("communities_sassybot_prob_chk", "communities", type_="check")
    op.drop_constraint("communities_sassybot_sass_chk", "communities", type_="check")
    for col in ("invoke_only", "probability", "sass_level", "enabled"):
        op.drop_column("communities", f"sassybot_{col}")
