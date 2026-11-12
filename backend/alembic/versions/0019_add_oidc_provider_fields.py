"""add oidc provider fields (discovery_url, claim_mapping)

Revision ID: 0019_add_oidc_provider_fields
Revises: a78f91338679
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_add_oidc_provider_fields"
down_revision: str | None = "a78f91338679"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("oauth_providers", sa.Column("discovery_url", sa.Text(), nullable=True))
    op.add_column(
        "oauth_providers",
        sa.Column(
            "claim_mapping",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("oauth_providers", "claim_mapping")
    op.drop_column("oauth_providers", "discovery_url")
