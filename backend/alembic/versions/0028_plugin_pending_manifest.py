"""add plugin pending_manifest field

Revision ID: 0028_plugin_pending_manifest
Revises: 0027_add_sso_only_to_branding
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0028_plugin_pending_manifest"
down_revision: str | None = "0027_add_sso_only_to_branding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("plugins", sa.Column("pending_manifest", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("plugins", "pending_manifest")
