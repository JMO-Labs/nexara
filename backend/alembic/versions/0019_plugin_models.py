"""add plugins and plugin_data tables

Revision ID: 0019_plugin_models
Revises: a78f91338679
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "0019_plugin_models"
down_revision: str | None = "a78f91338679"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_COMMUNITY = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "plugins",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column(
            "community_id",
            UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
            server_default=DEFAULT_COMMUNITY,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "permissions_granted", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("settings", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "installed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", "community_id"),
    )
    op.create_index("ix_plugins_id_community", "plugins", ["id", "community_id"])
    op.create_index("ix_plugins_deleted_at", "plugins", ["deleted_at"])

    op.create_table(
        "plugin_data",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.func.gen_random_uuid()
        ),
        sa.Column("plugin_id", sa.Text(), nullable=False),
        sa.Column(
            "community_id", UUID(as_uuid=True), nullable=False, server_default=DEFAULT_COMMUNITY
        ),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value_json", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["plugin_id", "community_id"],
            ["plugins.id", "plugins.community_id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("plugin_id", "community_id", "key", name="uq_plugin_data_key"),
    )


def downgrade() -> None:
    op.drop_table("plugin_data")
    op.drop_index("ix_plugins_deleted_at", table_name="plugins")
    op.drop_index("ix_plugins_id_community", table_name="plugins")
    op.drop_table("plugins")
