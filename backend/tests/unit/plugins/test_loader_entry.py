"""@file Unit tests for loader.import_entry package mode and task_loader."""

import json
import logging
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from app.plugins import loader, task_loader
from app.plugins.manifest import load_manifest


def _write(
    root: Path,
    pid: str,
    *,
    tasks: str | None = "tasks.py",
    perms=("celery_tasks",),
    mid: str | None = None,
    code: str = "LOADED = True\n",
    package: bool = False,
) -> Path:
    d = root / pid
    d.mkdir()
    backend = {"tasks": tasks} if tasks else {}
    (d / "manifest.json").write_text(
        json.dumps(
            {
                "id": mid or pid,
                "name": pid,
                "version": "1.0.0",
                "author": "a",
                "description": "d",
                "min_core_version": "0.1.0",
                "permissions": list(perms),
                "backend": backend,
            }
        )
    )
    if tasks:
        (d / tasks).write_text(code)
    if package:
        (d / "__init__.py").write_text("")
    return d


@pytest.fixture(autouse=True)
def _clean_modules():
    yield
    for m in [m for m in sys.modules if m.startswith("nexara_plugin_")]:
        del sys.modules[m]


def test_fresh_drops_stale_package_modules(tmp_path):
    d = _write(tmp_path, "fp", package=True)
    m = load_manifest(d)
    first = loader.import_entry(d, m, "tasks.py", fresh=False)
    second = loader.import_entry(d, m, "tasks.py", fresh=True)
    assert first is not second


def test_non_fresh_reuses_cached_module(tmp_path):
    d = _write(tmp_path, "rp", package=True)
    m = load_manifest(d)
    first = loader.import_entry(d, m, "tasks.py", fresh=False)
    assert loader.import_entry(d, m, "tasks.py", fresh=False) is first


def test_package_spec_none_raises(tmp_path):
    d = _write(tmp_path, "np", package=True)
    m = load_manifest(d)
    with (
        patch.object(loader.importlib.util, "spec_from_file_location", return_value=None),
        pytest.raises(ValueError, match="cannot import package"),
    ):
        loader.import_entry(d, m, "tasks.py")


def test_load_tasks_missing_dir(tmp_path):
    assert task_loader.load_plugin_tasks(tmp_path / "nope") == []


def test_load_tasks_imports_permitted_and_skips_others(tmp_path, caplog):
    _write(tmp_path, "aa")
    _write(tmp_path, "bb", perms=())  # lacks celery_tasks
    _write(tmp_path, "cc", tasks=None)  # no tasks entry
    _write(tmp_path, "dd", mid="other")  # id mismatch
    _write(tmp_path, "ee", code="raise RuntimeError('boom')\n")  # import failure
    (tmp_path / "ff").mkdir()  # no manifest
    (tmp_path / "file.txt").write_text("x")  # not a dir
    with caplog.at_level(logging.WARNING):
        assert task_loader.load_plugin_tasks(tmp_path) == ["aa"]
    assert "lacks celery_tasks" in caplog.text


def test_plugins_root_is_loader_default():
    assert task_loader.plugins_root() == loader.DEFAULT_PLUGINS_DIR


def test_celery_signal_registers_plugin_tasks():
    from app.tasks import celery_app as mod

    with patch("app.plugins.task_loader.load_plugin_tasks", return_value=["x"]) as lp:
        mod._load_plugin_tasks()
    lp.assert_called_once_with()
