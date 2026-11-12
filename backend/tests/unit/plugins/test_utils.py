"""@file test_utils.py
@brief Unit tests for plugin utility functions.
"""

import json

import pytest

from app.core.exceptions import ValidationError
from app.plugins.utils import get_plugin_module_name, validate_plugin_dir


def _manifest(pid="hello"):
    return json.dumps(
        {
            "id": pid,
            "name": "n",
            "version": "1.0.0",
            "author": "a",
            "description": "d",
            "min_core_version": "0.1.0",
        }
    )


def test_valid_dir(tmp_path):
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / "manifest.json").write_text(_manifest())
    assert validate_plugin_dir(tmp_path).id == "hello"


def test_missing_init(tmp_path):
    (tmp_path / "manifest.json").write_text(_manifest())
    with pytest.raises(ValidationError):
        validate_plugin_dir(tmp_path)


def test_missing_manifest(tmp_path):
    (tmp_path / "__init__.py").write_text("")
    with pytest.raises(ValidationError):
        validate_plugin_dir(tmp_path)


def test_bad_id(tmp_path):
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / "manifest.json").write_text(_manifest("Bad_ID"))
    with pytest.raises(ValidationError):
        validate_plugin_dir(tmp_path)


def test_not_a_dir(tmp_path):
    with pytest.raises(ValidationError):
        validate_plugin_dir(tmp_path / "nope")


def test_module_name():
    assert get_plugin_module_name("my-plugin") == "plugin_my_plugin"


@pytest.mark.parametrize("bad", ["", "../x", "A", "-a", "a-", "a b"])
def test_module_name_rejects(bad):
    with pytest.raises(ValidationError):
        get_plugin_module_name(bad)
