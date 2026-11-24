"""Out-of-process plugins.

@file 0076_plugins.py
@brief Drop in-process plugin tables; add plugin_* tables and posts.plugin_flags.

Revision ID: 0076_plugins
Revises: 0075_countdowns
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision = "0076_plugins"
down_revision = "0075_countdowns"
branch_labels = None
depends_on = None

_COMMUNITY = "00000000-0000-0000-0000-000000000001"
_NOW = sa.func.now()
_EMPTY_OBJ = sa.text("'{}'::jsonb")


def _community_col() -> sa.Column:
    return sa.Column(
        "community_id",
        pg.UUID(as_uuid=True),
        sa.ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=_COMMUNITY,
    )


def _install_fk() -> sa.Column:
    return sa.Column(
        "install_id",
        pg.UUID(as_uuid=True),
        sa.ForeignKey("plugin_installs.id", ondelete="CASCADE"),
        nullable=False,
    )


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )


def _ts(name: str, **kw) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), **kw)


def _drop_old() -> None:
    op.drop_index("ix_plugin_api_keys_plugin", table_name="plugin_api_keys")
    op.drop_table("plugin_api_keys")
    op.drop_table("plugin_data")
    op.drop_index("ix_plugins_deleted_at", table_name="plugins")
    op.drop_index("ix_plugins_id_community", table_name="plugins")
    op.drop_table("plugins")


def _recreate_old() -> None:
    """@brief Recreate legacy tables empty (DDL from 0022/0025/0028)."""
    op.create_table(
        "plugins",
        sa.Column("id", sa.Text(), nullable=False),
        _community_col(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("permissions_granted", pg.JSONB(), nullable=False,
                  server_default=sa.text("'[]'::jsonb")),
        sa.Column("settings", pg.JSONB(), nullable=False, server_default=_EMPTY_OBJ),
        _ts("installed_at", nullable=False, server_default=_NOW),
        _ts("updated_at", nullable=False, server_default=_NOW),
        _ts("deleted_at", nullable=True),
        sa.Column("pending_manifest", pg.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id", "community_id"),
    )  # fmt: skip
    op.create_index("ix_plugins_id_community", "plugins", ["id", "community_id"])
    op.create_index("ix_plugins_deleted_at", "plugins", ["deleted_at"])
    plugin_fk = sa.ForeignKeyConstraint(
        ["plugin_id", "community_id"], ["plugins.id", "plugins.community_id"], ondelete="CASCADE"
    )
    op.create_table(
        "plugin_data",
        _uuid_pk(),
        sa.Column("plugin_id", sa.Text(), nullable=False),
        sa.Column("community_id", pg.UUID(as_uuid=True), nullable=False, server_default=_COMMUNITY),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value_json", pg.JSONB(), nullable=False),
        _ts("created_at", nullable=False, server_default=_NOW),
        _ts("updated_at", nullable=False, server_default=_NOW),
        plugin_fk,
        sa.UniqueConstraint("plugin_id", "community_id", "key", name="uq_plugin_data_key"),
    )
    op.create_table(
        "plugin_api_keys",
        _uuid_pk(),
        sa.Column("plugin_id", sa.Text(), nullable=False),
        sa.Column("community_id", pg.UUID(as_uuid=True), nullable=False, server_default=_COMMUNITY),
        sa.Column("key_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("key_hint", sa.String(8), nullable=False),
        _ts("created_at", nullable=False, server_default=_NOW),
        _ts("last_used_at", nullable=True),
        _ts("revoked_at", nullable=True),
        sa.ForeignKeyConstraint(
            ["plugin_id", "community_id"],
            ["plugins.id", "plugins.community_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_plugin_api_keys_plugin", "plugin_api_keys", ["plugin_id", "community_id"])


def upgrade() -> None:
    """@brief Replace legacy plugin tables with the out-of-process model."""
    _drop_old()
    op.create_table(
        "plugin_installs",
        _uuid_pk(),
        sa.Column("plugin_id", sa.Text(), nullable=False, unique=True),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("manifest", pg.JSONB(), nullable=False),
        sa.Column("manifest_url", sa.Text()),
        sa.Column("endpoint_url", sa.Text()),
        sa.Column("package_url", sa.Text()),
        sa.Column("sha256", sa.Text()),
        sa.Column("source_index", sa.Text()),
        sa.Column("tier", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("granted_scopes", pg.ARRAY(sa.Text()), nullable=False,
                  server_default=sa.text("'{}'::text[]")),
        _ts("installed_at", nullable=False, server_default=_NOW),
        _ts("updated_at", nullable=False, server_default=_NOW),
        sa.CheckConstraint(
            "tier IS NULL OR tier IN ('official','verified','community')",
            name="plugin_installs_tier_check",
        ),
        sa.CheckConstraint(
            "status IN ('installing','running','disabled','failed','blocked')",
            name="plugin_installs_status_check",
        ),
    )  # fmt: skip
    op.create_table(
        "plugin_communities",
        _install_fk(),
        _community_col(),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("bot_user_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("settings", pg.JSONB(), nullable=False, server_default=_EMPTY_OBJ),
        sa.Column("webhook_secret", sa.Text()),
        sa.PrimaryKeyConstraint("install_id", "community_id"),
    )  # fmt: skip
    op.create_table(
        "plugin_tokens",
        _uuid_pk(),
        _install_fk(),
        _community_col(),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        _ts("created_at", nullable=False, server_default=_NOW),
        _ts("revoked_at", nullable=True),
    )
    op.create_index("ix_plugin_tokens_install", "plugin_tokens", ["install_id", "community_id"])
    op.create_table(
        "plugin_user_prefs",
        _install_fk(),
        sa.Column("user_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        _community_col(),
        sa.Column("values", pg.JSONB(), nullable=False, server_default=_EMPTY_OBJ),
        sa.PrimaryKeyConstraint("install_id", "user_id", "community_id"),
    )  # fmt: skip
    op.create_table(
        "plugin_indexes",
        _uuid_pk(),
        sa.Column("url", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _ts("last_fetched_at", nullable=True),
        sa.Column("last_error", sa.Text()),
    )
    op.add_column(
        "posts", sa.Column("plugin_flags", pg.JSONB(), nullable=False, server_default=_EMPTY_OBJ)
    )


def downgrade() -> None:
    """@brief Drop new tables; recreate legacy plugin tables empty."""
    op.drop_column("posts", "plugin_flags")
    op.drop_table("plugin_indexes")
    op.drop_table("plugin_user_prefs")
    op.drop_index("ix_plugin_tokens_install", table_name="plugin_tokens")
    op.drop_table("plugin_tokens")
    op.drop_table("plugin_communities")
    op.drop_table("plugin_installs")
    _recreate_old()
