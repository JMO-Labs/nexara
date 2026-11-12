"""add sso_only to community_branding

Revision ID: 0027_add_sso_only_to_branding
Revises: 0026_list_templates
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0027_add_sso_only_to_branding"
down_revision: str | None = "0026_list_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "community_branding",
        sa.Column("sso_only", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("community_branding", "sso_only")
