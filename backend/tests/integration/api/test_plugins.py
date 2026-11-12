"""
@file test_plugins.py
@brief Integration tests for the plugin registry API (/api/v1/plugins).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.plugins import get_plugin_service
from app.core.dependencies import get_current_user
from app.services.plugin_service import PluginService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class FakeRepo:
    """@brief In-memory plugin repository keyed by (id, community)."""

    def __init__(self) -> None:
        self.rows: dict[tuple[str, uuid.UUID], SimpleNamespace] = {}

    async def get(self, pid, cid, include_deleted=False):
        r = self.rows.get((pid, cid))
        return r if r and (include_deleted or r.deleted_at is None) else None

    async def list(self, cid):
        return [r for (_, c), r in self.rows.items() if c == cid and r.deleted_at is None]

    async def save(self, row):
        self.rows[(row.id, row.community_id)] = row
        return row


class FakeKeyRepo:
    """@brief In-memory API key repository."""

    def __init__(self) -> None:
        self.keys: list[SimpleNamespace] = []

    async def create(self, *, plugin_id, community_id, key_hash, key_hint):
        k = SimpleNamespace(plugin_id=plugin_id, community_id=community_id, revoked_at=None)
        self.keys.append(k)
        return k

    async def revoke_all(self, plugin_id, community_id):
        for k in self.keys:
            if k.plugin_id == plugin_id and k.community_id == community_id:
                k.revoked_at = datetime.now(UTC)


def _manifest(pid="hello", min_core="0.1.0", **extra):
    return {
        "id": pid,
        "name": "Hello",
        "version": "1.0.0",
        "author": "a",
        "description": "d",
        "min_core_version": min_core,
        "permissions": ["db_read"],
        "settings": {
            "greeting": {"type": "string", "label": "Greeting"},
            "token": {"type": "string", "label": "Token", "secret": True},
        },
        **extra,
    }


@pytest.fixture
def env(tmp_path: Path, test_app):
    """@brief Plugins dir with one valid plugin, fakes, and client factory."""
    d = tmp_path / "hello"
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps(_manifest()))
    repo, keys = FakeRepo(), FakeKeyRepo()
    svc = PluginService(repo, keys, CID, tmp_path, "0.1.0")
    test_app.dependency_overrides[get_plugin_service] = lambda: svc

    def client(role="admin"):
        user = SimpleNamespace(id=uuid.uuid4(), role=role, community_id=CID)
        test_app.dependency_overrides[get_current_user] = lambda: user
        return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")

    yield SimpleNamespace(client=client, repo=repo, keys=keys, dir=tmp_path)
    test_app.dependency_overrides.clear()


async def test_install_creates_entry_and_key(env):
    async with env.client() as c:
        r = await c.post("/api/v1/plugins/hello/install")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "hello" and body["is_enabled"] is False
    assert body["api_key"].startswith("nxr_plugin_hello_")
    assert ("hello", CID) in env.repo.rows and len(env.keys.keys) == 1


async def test_install_twice_conflicts(env):
    async with env.client() as c:
        await c.post("/api/v1/plugins/hello/install")
        r = await c.post("/api/v1/plugins/hello/install")
    assert r.status_code == 409


async def test_install_missing_dir_404(env):
    async with env.client() as c:
        r = await c.post("/api/v1/plugins/nope/install")
    assert r.status_code == 404


async def test_install_rejects_traversal_id(env):
    async with env.client() as c:
        r = await c.post("/api/v1/plugins/..%2Fx/install")
    assert r.status_code in (400, 404, 422)


async def test_install_incompatible_core_version(env):
    d = env.dir / "future"
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps(_manifest("future", min_core="9.0.0")))
    async with env.client() as c:
        r = await c.post("/api/v1/plugins/future/install")
    assert r.status_code == 422


async def test_install_invalid_manifest_422(env):
    d = env.dir / "bad"
    d.mkdir()
    (d / "manifest.json").write_text("{}")
    async with env.client() as c:
        r = await c.post("/api/v1/plugins/bad/install")
    assert r.status_code == 422


async def test_list_reports_is_enabled(env):
    async with env.client() as c:
        await c.post("/api/v1/plugins/hello/install")
        assert (await c.get("/api/v1/plugins")).json()[0]["is_enabled"] is False
        await c.put("/api/v1/plugins/hello/enable")
        lst = (await c.get("/api/v1/plugins")).json()
        assert lst[0]["is_enabled"] is True and lst[0]["name"] == "Hello"
        await c.put("/api/v1/plugins/hello/disable")
        assert (await c.get("/api/v1/plugins")).json()[0]["is_enabled"] is False


async def test_list_scoped_to_community(env):
    other = uuid.uuid4()
    env.repo.rows[("x", other)] = SimpleNamespace(
        id="x", community_id=other, name="X", version="1.0.0", is_enabled=True,
        deleted_at=None, settings={}, permissions_granted=[],
    )
    async with env.client("member") as c:
        assert (await c.get("/api/v1/plugins")).json() == []


async def test_manifest_accessible_to_member(env):
    async with env.client("member") as c:
        r = await c.get("/api/v1/plugins/hello/manifest")
    assert r.status_code == 200 and r.json()["id"] == "hello"


async def test_settings_save_and_read(env):
    async with env.client() as c:
        await c.post("/api/v1/plugins/hello/install")
        r = await c.put("/api/v1/plugins/hello/settings", json={"settings": {"greeting": "hi"}})
        assert r.status_code == 200
        got = await c.get("/api/v1/plugins/hello/settings")
    assert got.json()["settings"]["greeting"] == "hi"


async def test_settings_unknown_key_rejected(env):
    async with env.client() as c:
        await c.post("/api/v1/plugins/hello/install")
        r = await c.put("/api/v1/plugins/hello/settings", json={"settings": {"zzz": 1}})
    assert r.status_code == 422


async def test_secret_setting_masked_on_read(env):
    async with env.client() as c:
        await c.post("/api/v1/plugins/hello/install")
        await c.put("/api/v1/plugins/hello/settings", json={"settings": {"token": "s3cret"}})
        got = await c.get("/api/v1/plugins/hello/settings")
    assert "s3cret" not in got.text


async def test_uninstall_soft_deletes_and_revokes_keys(env):
    async with env.client() as c:
        await c.post("/api/v1/plugins/hello/install")
        r = await c.delete("/api/v1/plugins/hello")
        assert r.status_code == 200
        assert (await c.get("/api/v1/plugins")).json() == []
        again = await c.post("/api/v1/plugins/hello/install")
    assert env.repo.rows[("hello", CID)].deleted_at is None
    assert again.status_code == 200
    assert env.keys.keys[0].revoked_at is not None


async def test_unknown_plugin_404(env):
    async with env.client() as c:
        assert (await c.put("/api/v1/plugins/hello/enable")).status_code == 404
        assert (await c.get("/api/v1/plugins/hello/settings")).status_code == 404


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/v1/plugins/hello/install"),
        ("DELETE", "/api/v1/plugins/hello"),
        ("PUT", "/api/v1/plugins/hello/enable"),
        ("PUT", "/api/v1/plugins/hello/disable"),
        ("PUT", "/api/v1/plugins/hello/settings"),
    ],
)
async def test_admin_only_endpoints_403_for_member(env, method, path):
    async with env.client("member") as c:
        r = await c.request(method, path, json={"settings": {}})
    assert r.status_code == 403
