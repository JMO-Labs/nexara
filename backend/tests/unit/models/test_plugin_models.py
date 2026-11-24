"""
@file test_plugin_models.py
@brief Plugin model metadata checks.
"""

from app.models.plugin import (
    PluginCommunity,
    PluginIndex,
    PluginInstall,
    PluginToken,
    PluginUserPref,
)
from app.models.post import Post


def test_table_names() -> None:
    names = {
        m.__tablename__
        for m in (PluginInstall, PluginCommunity, PluginToken, PluginUserPref, PluginIndex)
    }
    assert names == {
        "plugin_installs",
        "plugin_communities",
        "plugin_tokens",
        "plugin_user_prefs",
        "plugin_indexes",
    }


def test_post_plugin_flags_and_pks() -> None:
    assert "plugin_flags" in Post.__table__.c
    assert [c.name for c in PluginCommunity.__table__.primary_key] == ["install_id", "community_id"]
    assert [c.name for c in PluginUserPref.__table__.primary_key] == ["install_id", "user_id"]
    assert PluginInstall.__table__.c.plugin_id.unique
    assert PluginToken.__table__.c.token_hash.unique
