"""
@file test_recipe_box.py
@brief Integration tests for the example-recipe-box plugin (router, task, hook).

PluginDB is replaced by an in-memory store that still enforces manifest permissions.
"""

from __future__ import annotations

import importlib
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.plugins.context import PluginContext
from app.plugins.hooks import HookRegistry
from app.plugins.loader import _import_module
from app.plugins.manifest import PluginManifest, PluginPermission, load_manifest
from app.plugins.permissions import enforce_permission

PLUGIN_DIR = Path(__file__).resolve().parents[4] / "plugins" / "example-recipe-box"
PKG = "nexara_plugin_example_recipe_box"
COMMUNITY = uuid.UUID("00000000-0000-0000-0000-000000000001")
ALICE, BOB, ADMIN = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


class FakeDB:
    """@brief In-memory stand-in for PluginDB with the same permission checks."""

    def __init__(self, manifest: PluginManifest) -> None:
        self.m, self.data = manifest, {}

    async def get(self, key: str) -> Any:
        enforce_permission(self.m, PluginPermission.DB_READ)
        return self.data.get(key)

    async def set(self, key: str, value: Any) -> None:
        enforce_permission(self.m, PluginPermission.DB_WRITE)
        self.data[key] = value

    async def delete(self, key: str) -> None:
        enforce_permission(self.m, PluginPermission.DB_WRITE)
        self.data.pop(key, None)


def _user(uid: uuid.UUID, role: str = "member") -> MagicMock:
    return MagicMock(id=uid, community_id=COMMUNITY, role=role, is_active=True)


def _make_ctx(manifest: PluginManifest, settings: dict | None = None) -> PluginContext:
    ctx = PluginContext("example-recipe-box", manifest, None, COMMUNITY, None, None, settings)
    object.__setattr__(ctx, "db", FakeDB(manifest))
    return ctx


@pytest.fixture
def manifest() -> PluginManifest:
    return load_manifest(PLUGIN_DIR)


@pytest.fixture
def env(manifest):
    """@brief (app, state) where state['user'] picks the caller and state['ctx'] the context."""
    mod = _import_module(PLUGIN_DIR, manifest)
    state: dict[str, Any] = {"user": _user(ALICE), "ctx": _make_ctx(manifest)}
    app = FastAPI()
    from app.core.exceptions import register_exception_handlers

    register_exception_handlers(app)
    app.include_router(mod.router, prefix="/api/v1/plugins/example-recipe-box")
    app.dependency_overrides[get_current_user] = lambda: state["user"]
    app.dependency_overrides[mod.get_ctx] = lambda: state["ctx"]
    return app, state


@pytest.fixture
async def client(env):
    app, _ = env
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


URL = "/api/v1/plugins/example-recipe-box/recipes"


def _body(name="Pancakes", tags=("breakfast",), ing="flour") -> dict:
    return {
        "name": name,
        "ingredients": [{"name": ing, "qty": 2, "unit": "cup"}],
        "steps": ["mix", "fry"],
        "tags": list(tags),
        "image_url": None,
    }


def test_manifest_declares_contract(manifest):
    perms = set(manifest.permissions)
    assert {"db_read", "db_write", "hooks_after_post_created", "storage_access"} <= perms
    assert manifest.settings["max_recipes_per_user"].default == 50


async def test_crud(client):
    r = await client.post(URL, json=_body())
    assert r.status_code == 201
    rid = r.json()["id"]
    assert (await client.get(f"{URL}/{rid}")).json()["name"] == "Pancakes"
    up = await client.put(f"{URL}/{rid}", json=_body(name="Crepes"))
    assert up.status_code == 200 and up.json()["name"] == "Crepes"
    assert (await client.delete(f"{URL}/{rid}")).status_code == 204
    gone = await client.get(f"{URL}/{rid}")
    assert gone.status_code == 404 and gone.json()["error"]["code"]


async def test_list_pagination_and_tag_filter(client):
    for i in range(3):
        await client.post(URL, json=_body(name=f"R{i}", tags=["a"] if i else ["b"]))
    page = (await client.get(URL, params={"limit": 2})).json()
    assert page["total"] == 3 and len(page["items"]) == 2
    tagged = (await client.get(URL, params={"tag": "b"})).json()
    assert [x["name"] for x in tagged["items"]] == ["R0"]


async def test_search_by_name_and_ingredient(client):
    await client.post(URL, json=_body(name="Pancakes", ing="flour"))
    await client.post(URL, json=_body(name="Salad", ing="lettuce"))
    by_name = (await client.get(f"{URL}/search", params={"q": "panc"})).json()
    assert [x["name"] for x in by_name["items"]] == ["Pancakes"]
    by_ing = (await client.get(f"{URL}/search", params={"q": "LETTUCE"})).json()
    assert [x["name"] for x in by_ing["items"]] == ["Salad"]


async def test_owner_isolation_and_admin_access(client, env):
    _, state = env
    rid = (await client.post(URL, json=_body())).json()["id"]
    state["user"] = _user(BOB)
    assert (await client.get(f"{URL}/{rid}")).status_code == 404
    assert (await client.get(URL)).json()["total"] == 0
    assert (await client.put(f"{URL}/{rid}", json=_body())).status_code == 404
    assert (await client.delete(f"{URL}/{rid}")).status_code == 404
    state["user"] = _user(ADMIN, "admin")
    assert (await client.get(f"{URL}/{rid}")).status_code == 200
    assert (await client.get(URL)).json()["total"] == 1
    assert (await client.put(f"{URL}/{rid}", json=_body())).status_code == 403
    assert (await client.delete(f"{URL}/{rid}")).status_code == 403


async def test_rate_limit_429(client, env, manifest):
    _, state = env
    state["ctx"] = _make_ctx(manifest, {"max_recipes_per_user": 2})
    assert (await client.post(URL, json=_body())).status_code == 201
    assert (await client.post(URL, json=_body())).status_code == 201
    r = await client.post(URL, json=_body())
    assert r.status_code == 429 and "error" in r.json()


async def test_default_limit_is_50(client):
    for _ in range(50):
        assert (await client.post(URL, json=_body())).status_code == 201
    assert (await client.post(URL, json=_body())).status_code == 429


@pytest.mark.parametrize("missing", ["db_read", "db_write"])
@pytest.mark.parametrize(
    "method,path",
    [("post", ""), ("get", ""), ("get", "/x"), ("put", "/x"), ("delete", "/x"), ("get", "/search")],
)
async def test_missing_permission_is_403(client, env, manifest, missing, method, path):
    _, state = env
    data = manifest.model_dump()
    data["permissions"] = [p for p in data["permissions"] if p != missing]
    state["ctx"] = _make_ctx(PluginManifest.model_validate(data))
    kw = {"json": _body()} if method in ("post", "put") else {}
    r = await getattr(client, method)(URL + path, **kw)
    assert r.status_code == 403
    assert r.json()["error"]["code"]


async def test_daily_task_caches_random_recipe(manifest):
    tasks = importlib.import_module(f"{PKG}.tasks")
    store = importlib.import_module(f"{PKG}.store")
    ctx = _make_ctx(manifest)
    cache = MagicMock()
    sets: dict[str, Any] = {}

    async def _set(key, value, ex=None):
        sets[key] = value

    cache.set = _set
    assert await tasks.pick_recipe_of_day(ctx, cache) is None
    rec = await store.create(ctx, ALICE, store.RecipeIn(name="Soup"), limit=5)
    picked = await tasks.pick_recipe_of_day(ctx, cache)
    assert picked == rec["id"]
    assert any(rec["id"] in v for v in sets.values())


async def test_hook_suggests_recipe_tag(manifest):
    HookRegistry.reset()
    hooks = importlib.import_module(f"{PKG}.hooks")
    ctx = _make_ctx(manifest)
    pid = uuid.uuid4()
    await hooks.on_post_created(
        ctx, user_id=ALICE, post_id=pid, content="My Recipe for jam", subgroup_id=None
    )
    assert (await ctx.db.get(f"suggestion:{pid}"))["tag"] == "recipe"
    other = uuid.uuid4()
    await hooks.on_post_created(
        ctx, user_id=ALICE, post_id=other, content="hello", subgroup_id=None
    )
    assert await ctx.db.get(f"suggestion:{other}") is None


async def test_register_hooks_registers_handler(manifest):
    HookRegistry.reset()
    hooks = importlib.import_module(f"{PKG}.hooks")
    hooks.register_hooks(COMMUNITY, manifest)
    assert [e.plugin_id for e in HookRegistry._hooks[(COMMUNITY, "after_post_created")]] == [
        "example-recipe-box"
    ]
    HookRegistry.reset()
