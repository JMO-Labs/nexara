"""@file Unit tests for plugin manifest validation."""

import json

import pytest
from packaging.version import InvalidVersion
from pydantic import ValidationError

from app.plugins import manifest as manifest_mod
from app.plugins.manifest import (
    PluginManifest,
    PluginPermission,
    is_compatible,
    load_manifest,
)

VALID = {
    "id": "hello",
    "name": "Hello",
    "version": "1.2.3",
    "author": "Jane",
    "description": "Demo",
    "min_core_version": "0.1.0",
    "permissions": ["db_read", "send_notifications"],
    "hooks": {"before_post_created": "Check posts"},
    "settings": {"api_key": {"type": "string", "label": "Key", "required": True, "secret": True}},
    "backend": {"routes": "routes.py", "tasks": "tasks.py"},
    "frontend": {"slots": {"sidebar": "Widget"}},
}


class TestManifest:
    def test_valid_parses(self):
        m = PluginManifest.model_validate(VALID)
        assert m.version == "1.2.3"
        assert PluginPermission.DB_READ in m.permissions
        assert m.settings["api_key"].secret is True

    @pytest.mark.parametrize("field", ["version", "min_core_version"])
    @pytest.mark.parametrize("bad", ["1.0", "v1", "abc", "1.2.3.4", "1.2.3-beta"])
    def test_bad_semver(self, field, bad):
        with pytest.raises(ValidationError):
            PluginManifest.model_validate({**VALID, field: bad})

    def test_invalid_version_from_packaging_is_wrapped(self, monkeypatch):
        def boom(_value):
            raise InvalidVersion("boom")

        monkeypatch.setattr(manifest_mod, "Version", boom)
        with pytest.raises(ValidationError, match="boom"):
            PluginManifest.model_validate(VALID)

    def test_unknown_permission(self):
        with pytest.raises(ValidationError):
            PluginManifest.model_validate({**VALID, "permissions": ["root"]})

    def test_duplicate_permissions_rejected(self):
        with pytest.raises(ValidationError):
            PluginManifest.model_validate({**VALID, "permissions": ["db_read", "db_read"]})

    def test_missing_required(self):
        data = {k: v for k, v in VALID.items() if k != "name"}
        with pytest.raises(ValidationError):
            PluginManifest.model_validate(data)

    def test_duplicate_hooks_rejected_in_json(self, tmp_path):
        d = tmp_path / "p"
        d.mkdir()
        (d / "manifest.json").write_text(
            '{"id":"p","name":"P","version":"1.0.0","author":"a","description":"d",'
            '"min_core_version":"0.1.0","hooks":{"x":"a","x":"b"}}'
        )
        with pytest.raises(ValidationError):
            load_manifest(d)

    def test_setting_bad_type(self):
        bad = {**VALID, "settings": {"k": {"type": "blob", "label": "K"}}}
        with pytest.raises(ValidationError):
            PluginManifest.model_validate(bad)


class TestCompatibility:
    def test_core_meets_min(self):
        m = PluginManifest.model_validate({**VALID, "min_core_version": "1.2.0"})
        assert is_compatible(m, "1.2.0")
        assert is_compatible(m, "2.0.0")

    def test_core_too_old(self):
        m = PluginManifest.model_validate({**VALID, "min_core_version": "1.2.0"})
        assert not is_compatible(m, "1.1.9")


class TestLoad:
    def test_load_json(self, tmp_path):
        (tmp_path / "manifest.json").write_text(json.dumps(VALID))
        assert load_manifest(tmp_path).id == "hello"

    def test_load_toml(self, tmp_path):
        (tmp_path / "manifest.toml").write_text(
            'id="hello"\nname="Hello"\nversion="1.0.0"\nauthor="a"\ndescription="d"\n'
            'min_core_version="0.1.0"\npermissions=["db_write"]\n'
            '[hooks]\non_user_joined="joined"\n'
        )
        m = load_manifest(tmp_path)
        assert m.permissions == [PluginPermission.DB_WRITE]
        assert "on_user_joined" in m.hooks

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_manifest(tmp_path)
