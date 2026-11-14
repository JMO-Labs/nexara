"""@file Unit tests for the plugin loader and registry."""

import json
import logging
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI

from app.plugins.loader import load_plugins
from app.plugins.registry import PluginRegistry
from tests.unit.route_paths import route_paths

CID = uuid.uuid4()


def manifest(pid: str, routes: str | None = "routes.py") -> dict:
    return {
        "id": pid,
        "name": pid,
        "version": "1.0.0",
        "author": "a",
        "description": "d",
        "min_core_version": "0.1.0",
        "backend": {"routes": routes} if routes else {},
    }


def make_plugin(root: Path, pid: str, *, code: str | None = None, routes="routes.py") -> None:
    d = root / pid
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps(manifest(pid, routes)))
    if code is None:
        code = (
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
            "@router.get('/ping')\n"
            "async def ping():\n"
            f"    return {{'id': '{pid}'}}\n"
        )
    if routes:
        (d / routes).write_text(code)


def session_with(enabled: list[str]) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = enabled
    session.execute.return_value = result
    return session


@pytest.fixture(autouse=True)
def _reset() -> None:
    PluginRegistry.reset()


def paths(app: FastAPI) -> set[str]:
    return route_paths(app)


async def test_valid_plugin_loaded(tmp_path, caplog):
    make_plugin(tmp_path, "alpha")
    app = FastAPI()
    with caplog.at_level(logging.INFO):
        await load_plugins(app, session_with(["alpha"]), CID, plugins_dir=tmp_path)
    assert PluginRegistry.get("alpha") is not None
    assert [p.manifest.id for p in PluginRegistry.list()] == ["alpha"]
    assert any("alpha" in r.getMessage() and r.levelno == logging.INFO for r in caplog.records)


async def test_router_mounted_at_prefix(tmp_path):
    make_plugin(tmp_path, "alpha")
    app = FastAPI()
    await load_plugins(app, session_with(["alpha"]), CID, plugins_dir=tmp_path)
    assert "/api/v1/plugins/alpha/ping" in paths(app)


async def test_invalid_manifest_skipped_and_logged(tmp_path, caplog):
    make_plugin(tmp_path, "good")
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "manifest.json").write_text("{not json")
    with caplog.at_level(logging.INFO):
        await load_plugins(FastAPI(), session_with(["good", "bad"]), CID, plugins_dir=tmp_path)
    assert PluginRegistry.get("bad") is None
    assert PluginRegistry.get("good") is not None
    assert any(r.levelno >= logging.ERROR and "bad" in r.getMessage() for r in caplog.records)


async def test_import_failure_skipped(tmp_path):
    make_plugin(tmp_path, "boom", code="raise RuntimeError('x')\n")
    await load_plugins(FastAPI(), session_with(["boom"]), CID, plugins_dir=tmp_path)
    assert PluginRegistry.get("boom") is None


async def test_disabled_or_uninstalled_skipped(tmp_path):
    make_plugin(tmp_path, "off")
    make_plugin(tmp_path, "on")
    app = FastAPI()
    await load_plugins(app, session_with(["on"]), CID, plugins_dir=tmp_path)
    assert PluginRegistry.get("off") is None
    assert "/api/v1/plugins/off/ping" not in paths(app)


async def test_multiple_plugins_alphabetical_no_collision(tmp_path):
    for pid in ("zeta", "alpha", "mid"):
        make_plugin(tmp_path, pid)
    app = FastAPI()
    await load_plugins(app, session_with(["zeta", "alpha", "mid"]), CID, plugins_dir=tmp_path)
    assert [p.manifest.id for p in PluginRegistry.list()] == ["alpha", "mid", "zeta"]
    for pid in ("zeta", "alpha", "mid"):
        assert f"/api/v1/plugins/{pid}/ping" in paths(app)


async def test_plugin_without_module_loads(tmp_path):
    make_plugin(tmp_path, "bare", routes=None)
    await load_plugins(FastAPI(), session_with(["bare"]), CID, plugins_dir=tmp_path)
    assert PluginRegistry.get("bare").module is None


async def test_routes_path_escape_rejected(tmp_path):
    make_plugin(tmp_path, "evil", routes="../outside.py")
    await load_plugins(FastAPI(), session_with(["evil"]), CID, plugins_dir=tmp_path)
    assert PluginRegistry.get("evil") is None


async def test_missing_dir_is_noop(tmp_path):
    await load_plugins(FastAPI(), session_with([]), CID, plugins_dir=tmp_path / "nope")
    assert PluginRegistry.list() == []


async def test_manifest_id_directory_mismatch_skipped(tmp_path, caplog):
    make_plugin(tmp_path, "alpha")
    (tmp_path / "alpha").rename(tmp_path / "other")
    with caplog.at_level(logging.ERROR):
        await load_plugins(FastAPI(), session_with(["alpha", "other"]), CID, plugins_dir=tmp_path)
    assert PluginRegistry.list() == []
    assert any("failed to load" in r.getMessage() for r in caplog.records)


async def test_unimportable_spec_skipped(tmp_path, monkeypatch):
    make_plugin(tmp_path, "alpha")
    monkeypatch.setattr("importlib.util.spec_from_file_location", lambda *a, **k: None)
    await load_plugins(FastAPI(), session_with(["alpha"]), CID, plugins_dir=tmp_path)
    assert PluginRegistry.get("alpha") is None


async def test_package_plugin_relative_import_and_register_hooks(tmp_path):
    d = tmp_path / "pk"
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps(manifest("pk")))
    (d / "__init__.py").write_text("")
    (d / "helper.py").write_text("VALUE = 7\n")
    (d / "routes.py").write_text(
        "from fastapi import APIRouter\nfrom .helper import VALUE\n"
        "router = APIRouter()\nCALLS = []\n"
        "def register_hooks(community_id, manifest):\n    CALLS.append((community_id, VALUE))\n"
    )
    cid = uuid.uuid4()
    await load_plugins(FastAPI(), session_with(["pk"]), cid, tmp_path)
    assert PluginRegistry.get("pk").module.CALLS == [(cid, 7)]
