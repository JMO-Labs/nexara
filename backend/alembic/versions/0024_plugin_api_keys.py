"""add plugin_api_keys table

Revision ID: 0024_plugin_api_keys
Revises: 0023_bookmarks
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0024_plugin_api_keys"
down_revision: str | Sequence[str] | None = "0023_bookmarks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_COMMUNITY = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "plugin_api_keys",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("plugin_id", sa.Text(), nullable=False),
        sa.Column(
            "community_id", UUID(as_uuid=True), nullable=False, server_default=DEFAULT_COMMUNITY
        ),
        sa.Column("key_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("key_hint", sa.String(8), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["plugin_id", "community_id"],
            ["plugins.id", "plugins.community_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_plugin_api_keys_plugin", "plugin_api_keys", ["plugin_id", "community_id"])


def downgrade() -> None:
    op.drop_index("ix_plugin_api_keys_plugin", table_name="plugin_api_keys")
    op.drop_table("plugin_api_keys")
