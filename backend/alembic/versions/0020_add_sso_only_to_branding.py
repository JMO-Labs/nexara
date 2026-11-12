"""add sso_only to community_branding

Revision ID: 0020_add_sso_only_to_branding
Revises: 0019_add_oidc_provider_fields
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0020_add_sso_only_to_branding"
down_revision: str | None = "0020_add_recipient_to_posts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "community_branding",
        sa.Column("sso_only", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("community_branding", "sso_only")
