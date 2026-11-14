"""
@file test_plugin_tasks.py
@brief Unit tests for the bundled-plugin task loader in plugin_tasks.py.
"""

import importlib
import sys
from unittest.mock import patch

from app.tasks import plugin_tasks


def test_plugins_dir_points_at_repo_plugins():
    assert plugin_tasks._PLUGINS.name == "plugins"
    assert (plugin_tasks._PLUGINS / "example-trivia" / "tasks.py").is_file()


def test_reload_loads_trivia_tasks_module():
    sys.modules.pop("nexara_plugin_example_trivia_tasks", None)
    importlib.reload(plugin_tasks)
    assert "nexara_plugin_example_trivia_tasks" in sys.modules


def test_load_skips_when_already_in_sys_modules():
    name = "nexara_plugin_my_plug_tasks"
    sentinel = object()
    with patch.dict(sys.modules, {name: sentinel}):
        plugin_tasks._load("my-plug", "tasks")
        assert sys.modules[name] is sentinel


def test_load_skips_missing_file():
    plugin_tasks._load("no-such-plugin", "tasks")
    assert "nexara_plugin_no_such_plugin_tasks" not in sys.modules


def test_load_returns_when_spec_is_none(tmp_path):
    (tmp_path / "p").mkdir()
    (tmp_path / "p" / "tasks.py").write_text("X = 1\n")
    with (
        patch.object(plugin_tasks, "_PLUGINS", tmp_path),
        patch("importlib.util.spec_from_file_location", return_value=None),
    ):
        plugin_tasks._load("p", "tasks")
    assert "nexara_plugin_p_tasks" not in sys.modules


def test_load_executes_module_and_registers_in_sys_modules(tmp_path):
    (tmp_path / "my-p").mkdir()
    (tmp_path / "my-p" / "tasks.py").write_text("X = 42\n")
    name = "nexara_plugin_my_p_tasks"
    try:
        with patch.object(plugin_tasks, "_PLUGINS", tmp_path):
            plugin_tasks._load("my-p", "tasks")
        assert sys.modules[name].X == 42
    finally:
        sys.modules.pop(name, None)
