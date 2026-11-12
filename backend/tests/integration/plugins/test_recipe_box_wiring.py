"""
@file test_recipe_box_wiring.py
@brief Runtime wiring of example-recipe-box: hook via load_plugins, task via Celery.
"""

from __future__ import annotations

import importlib
import sys
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from celery import signals
from fastapi import FastAPI

from app.plugins import task_loader
from app.plugins.context import PluginContext
from app.plugins.hooks import HookRegistry
from app.plugins.loader import load_plugins
from app.plugins.manifest import load_manifest
from app.plugins.registry import PluginRegistry
from app.tasks.celery_app import celery_app

PLUGINS_ROOT = Path(__file__).resolve().parents[4] / "plugins"
PID = "example-recipe-box"
TASK = f"plugins.{PID}.generate_recipe_of_day"
BEAT_KEY = f"{PID}-recipe-of-day"
COMMUNITY = uuid.uuid4()
PKG = "nexara_plugin_example_recipe_box"


@pytest.fixture(autouse=True)
def _clean():
    HookRegistry.reset()
    PluginRegistry.reset()
    celery_app.tasks.pop(TASK, None)
    for mod in [m for m in sys.modules if m.startswith(PKG)]:
        del sys.modules[mod]
    celery_app.conf.beat_schedule.pop(BEAT_KEY, None)
    yield
    HookRegistry.reset()
    PluginRegistry.reset()


def _session(enabled: list[str]) -> AsyncMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = enabled
    session = AsyncMock()
    session.execute.return_value = result
    return session


class _MemDB:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}

    async def set(self, key: str, value: Any) -> None:
        self.data[key] = value


async def test_load_plugins_registers_hook_that_stores_suggestion():
    await load_plugins(FastAPI(), _session([PID]), COMMUNITY, PLUGINS_ROOT)
    entries = HookRegistry._hooks[(COMMUNITY, "after_post_created")]
    assert [e.plugin_id for e in entries] == [PID]

    manifest = load_manifest(PLUGINS_ROOT / PID)
    ctx = PluginContext(PID, manifest, None, COMMUNITY, None, None)
    db = _MemDB()
    object.__setattr__(ctx, "db", db)
    post_id = uuid.uuid4()
    await entries[0].handler(ctx, user_id=uuid.uuid4(), post_id=post_id, content="a recipe")
    assert db.data[f"suggestion:{post_id}"]["tag"] == "recipe"


def test_load_plugin_tasks_registers_task_and_beat_entry():
    assert task_loader.load_plugin_tasks(PLUGINS_ROOT) == [PID]
    assert TASK in celery_app.tasks
    assert celery_app.conf.beat_schedule[BEAT_KEY]["task"] == TASK


def test_worker_import_signal_loads_plugin_tasks(monkeypatch):
    monkeypatch.setattr(task_loader, "plugins_root", lambda: PLUGINS_ROOT)
    signals.import_modules.send(sender=celery_app)
    assert TASK in celery_app.tasks
    assert BEAT_KEY in celery_app.conf.beat_schedule


def test_task_loader_requires_celery_tasks_permission(tmp_path):
    d = tmp_path / "nope"
    d.mkdir()
    (d / "manifest.toml").write_text(
        'id = "nope"\nname = "n"\nversion = "1.0.0"\nauthor = "a"\n'
        'description = "d"\nmin_core_version = "0.1.0"\npermissions = []\n'
        '[backend]\ntasks = "tasks.py"\n'
    )
    (d / "tasks.py").write_text("raise RuntimeError('must not import')\n")
    assert task_loader.load_plugin_tasks(tmp_path) == []


@pytest.mark.parametrize(("value", "expected"), [(True, True), (False, False), (None, False)])
async def test_task_checks_plugin_enabled(value, expected):
    task_loader.load_plugin_tasks(PLUGINS_ROOT)
    tasks = importlib.import_module(f"{PKG}.tasks")
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=value))
    assert await tasks._enabled(session, COMMUNITY) is expected
