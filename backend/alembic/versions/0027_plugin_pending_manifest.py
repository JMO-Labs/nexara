"""add plugin pending_manifest field

Revision ID: 0027_plugin_pending_manifest
Revises: 0026_list_templates
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0027_plugin_pending_manifest"
down_revision: str | None = "0026_list_templates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("plugins", sa.Column("pending_manifest", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("plugins", "pending_manifest")
