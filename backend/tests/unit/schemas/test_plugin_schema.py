"""
@file test_plugin_schema.py
@brief Strict validation tests for PluginRead and PluginDataRead.
"""

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.plugin import Plugin, PluginData
from app.schemas.plugin import PluginDataRead, PluginRead

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(UTC)


def _plugin(**over) -> Plugin:
    kw = dict(
        id="recipes",
        community_id=CID,
        name="Recipes",
        version="1.0.0",
        is_enabled=True,
        permissions_granted=["read"],
        settings={},
        installed_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )
    kw.update(over)
    return Plugin(**kw)


def _data(**over) -> PluginData:
    kw = dict(
        id=uuid.uuid4(),
        plugin_id="recipes",
        community_id=CID,
        key="k",
        value_json={"a": 1},
        created_at=NOW,
        updated_at=NOW,
    )
    kw.update(over)
    return PluginData(**kw)


def test_plugin_read_from_model():
    r = PluginRead.model_validate(_plugin())
    assert r.id == "recipes" and r.is_enabled is True and r.deleted_at is None


def test_plugin_data_read_from_model():
    r = PluginDataRead.model_validate(_data())
    assert r.key == "k" and r.value_json == {"a": 1}


def test_rejects_string_bool():
    with pytest.raises(ValidationError):
        PluginRead.model_validate(_plugin(is_enabled="yes"))


def test_rejects_dict_permissions():
    with pytest.raises(ValidationError):
        PluginRead.model_validate(_plugin(permissions_granted={"a": 1}))


def test_data_rejects_non_uuid_id():
    with pytest.raises(ValidationError):
        PluginDataRead.model_validate(_data(id="not-a-uuid"))
