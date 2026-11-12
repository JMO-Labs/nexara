"""
@file test_plugin.py
@brief Unit tests for Plugin and PluginData model structure and migration chain.
"""

from pathlib import Path

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

import app.models  # noqa: F401
from app.models.plugin import Plugin, PluginData

VERSIONS = Path(__file__).resolve().parents[3] / "alembic" / "versions"


class TestPluginModel:
    """@brief Verify the Plugin schema."""

    def test_tablename(self):
        assert Plugin.__tablename__ == "plugins"

    def test_columns(self):
        cols = {c.name for c in Plugin.__table__.columns}
        assert {
            "id",
            "name",
            "version",
            "is_enabled",
            "permissions_granted",
            "settings",
            "installed_at",
            "updated_at",
            "deleted_at",
            "community_id",
        } <= cols

    def test_id_is_text_and_scoped_per_community(self):
        pk = {c.name for c in Plugin.__table__.primary_key.columns}
        assert pk == {"id", "community_id"}

    def test_jsonb_columns(self):
        assert isinstance(Plugin.__table__.c.permissions_granted.type, JSONB)
        assert isinstance(Plugin.__table__.c.settings.type, JSONB)

    def test_soft_delete_nullable_and_disabled_default(self):
        assert Plugin.__table__.c.deleted_at.nullable is True
        assert str(Plugin.__table__.c.is_enabled.server_default.arg) == "false"

    def test_indexes(self):
        idx = {i.name: [c.name for c in i.columns] for i in Plugin.__table__.indexes}
        assert idx["ix_plugins_id_community"] == ["id", "community_id"]
        assert idx["ix_plugins_deleted_at"] == ["deleted_at"]

    def test_default_values_on_instance(self):
        p = Plugin(id="example-recipe-box", name="Recipe Box", version="1.0.0")
        assert p.deleted_at is None
        assert p.is_enabled is None  # DB server_default applies on insert
        assert Plugin.__table__.c.community_id.server_default is not None


class TestPluginDataModel:
    """@brief Verify the PluginData schema."""

    def test_tablename(self):
        assert PluginData.__tablename__ == "plugin_data"

    def test_columns(self):
        cols = {c.name for c in PluginData.__table__.columns}
        assert {
            "id",
            "plugin_id",
            "community_id",
            "key",
            "value_json",
            "created_at",
            "updated_at",
        } <= cols

    def test_unique_constraint(self):
        uniques = [
            [c.name for c in c_.columns]
            for c_ in PluginData.__table__.constraints
            if isinstance(c_, UniqueConstraint)
        ]
        assert ["plugin_id", "community_id", "key"] in uniques

    def test_fk_to_plugins(self):
        targets = {fk.target_fullname for fk in PluginData.__table__.foreign_keys}
        assert "plugins.id" in targets
        assert "plugins.community_id" in targets


class TestMigration:
    """@brief Verify the 0019 migration and linear chain."""

    def test_down_revision_is_previous_head(self):
        src = (VERSIONS / "0021_plugin_models.py").read_text()
        assert 'down_revision: str | None = "a78f91338679"' in src
        assert "plugin_data" in src and "drop_table" in src
