"""
@file test_plugin_lifecycle.py
@brief Integration tests for the admin plugin install/upgrade confirmation flow.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.admin_plugins import get_audit_repo
from app.api.v1.plugins import get_plugin_service
from app.core.dependencies import get_current_user
from app.services.plugin_lifecycle import PluginLifecycleService
from tests.integration.api.test_plugins import CID, FakeKeyRepo, FakeRepo, _manifest

BASE = "/api/v1/admin/plugins"


class FakeAudit:
    """@brief Records audit entries."""

    def __init__(self) -> None:
        self.entries: list[dict] = []

    async def append(self, **kw):
        self.entries.append(kw)


def _write(d: Path, **over) -> None:
    d.mkdir(exist_ok=True)
    (d / "manifest.json").write_text(json.dumps({**_manifest(), **over}))
    (d / "__init__.py").write_text("")


@pytest.fixture
def env(tmp_path: Path, test_app):
    """@brief Plugins dir with one plugin, fakes and client factory."""
    _write(tmp_path / "hello")
    repo, keys, audit = FakeRepo(), FakeKeyRepo(), FakeAudit()
    svc = PluginLifecycleService(repo, keys, CID, tmp_path, "0.1.0")
    test_app.dependency_overrides[get_plugin_service] = lambda: svc
    test_app.dependency_overrides[get_audit_repo] = lambda: audit

    def client(role="admin"):
        user = SimpleNamespace(id=uuid.uuid4(), role=role, community_id=CID)
        test_app.dependency_overrides[get_current_user] = lambda: user
        return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")

    yield SimpleNamespace(client=client, repo=repo, keys=keys, audit=audit, dir=tmp_path)
    test_app.dependency_overrides.clear()


async def test_install_request_returns_permissions_and_does_not_enable(env):
    async with env.client() as c:
        r = await c.post(f"{BASE}/install-request", json={"plugin_id": "hello"})
    assert r.status_code == 200
    b = r.json()
    assert b["permissions_requested"] == ["db_read"]
    assert b["new_permissions"] == ["db_read"]
    assert b["permissions_previously_granted"] == [] and b["removed_permissions"] == []
    assert b["manifest"]["id"] == "hello"
    assert not [x for x in env.repo.rows.values() if x.deleted_at is None]


async def test_install_confirm_creates_plugin(env):
    async with env.client() as c:
        await c.post(f"{BASE}/install-request", json={"plugin_id": "hello"})
        r = await c.post(f"{BASE}/install-confirm", json={"plugin_id": "hello"})
    assert r.status_code == 200
    row = env.repo.rows[("hello", CID)]
    assert row.is_enabled is True and row.deleted_at is None and row.pending_manifest is None
    assert row.permissions_granted == ["db_read"]
    assert r.json()["api_key"].startswith("nxr_plugin_hello_")
    assert len(env.keys.keys) == 1


async def test_confirm_without_request_404(env):
    async with env.client() as c:
        r = await c.post(f"{BASE}/install-confirm", json={"plugin_id": "hello"})
    assert r.status_code == 404


async def test_install_request_already_installed_conflicts(env):
    async with env.client() as c:
        await c.post(f"{BASE}/install-request", json={"plugin_id": "hello"})
        await c.post(f"{BASE}/install-confirm", json={"plugin_id": "hello"})
        r = await c.post(f"{BASE}/install-request", json={"plugin_id": "hello"})
    assert r.status_code == 409


async def test_expired_staged_install_cannot_be_confirmed(env):
    async with env.client() as c:
        await c.post(f"{BASE}/install-request", json={"plugin_id": "hello"})
        row = env.repo.rows[("hello", CID)]
        row.pending_manifest["staged_at"] = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        r = await c.post(f"{BASE}/install-confirm", json={"plugin_id": "hello"})
    assert r.status_code == 410
    assert env.repo.rows[("hello", CID)].deleted_at is not None


async def test_member_forbidden(env):
    async with env.client("member") as c:
        r = await c.post(f"{BASE}/install-request", json={"plugin_id": "hello"})
    assert r.status_code == 403


async def _installed(env, c):
    await c.post(f"{BASE}/install-request", json={"plugin_id": "hello"})
    await c.post(f"{BASE}/install-confirm", json={"plugin_id": "hello"})


async def test_upgrade_diff_then_confirm(env):
    async with env.client() as c:
        await _installed(env, c)
        _write(env.dir / "hello", version="1.1.0", permissions=["external_http"])
        r = await c.put(f"{BASE}/hello/upgrade", json={})
        assert r.status_code == 200
        b = r.json()
        assert b["current_version"] == "1.0.0" and b["new_version"] == "1.1.0"
        assert b["new_permissions"] == ["external_http"]
        assert b["removed_permissions"] == ["db_read"]
        assert b["permissions_previously_granted"] == ["db_read"]
        assert env.repo.rows[("hello", CID)].version == "1.0.0"
        r = await c.put(f"{BASE}/hello/upgrade", json={"confirm": True})
    assert r.status_code == 200
    row = env.repo.rows[("hello", CID)]
    assert row.version == "1.1.0" and row.permissions_granted == ["external_http"]
    assert row.pending_manifest is None


async def test_upgrade_incompatible_core_rejected(env):
    async with env.client() as c:
        await _installed(env, c)
        _write(env.dir / "hello", version="1.1.0", min_core_version="9.0.0")
        r = await c.put(f"{BASE}/hello/upgrade", json={})
    assert r.status_code == 422


async def test_upgrade_no_newer_version_rejected(env):
    async with env.client() as c:
        await _installed(env, c)
        r = await c.put(f"{BASE}/hello/upgrade", json={})
    assert r.status_code == 422


async def test_upgrade_confirm_requires_staging(env):
    async with env.client() as c:
        await _installed(env, c)
        _write(env.dir / "hello", version="1.1.0")
        r = await c.put(f"{BASE}/hello/upgrade", json={"confirm": True})
    assert r.status_code == 404


async def test_audit_entries_for_lifecycle(env):
    async with env.client() as c:
        await _installed(env, c)
        _write(env.dir / "hello", version="1.1.0", permissions=["db_read", "db_write"])
        await c.put(f"{BASE}/hello/upgrade", json={})
        await c.put(f"{BASE}/hello/upgrade", json={"confirm": True})
    actions = [e["action"] for e in env.audit.entries]
    assert actions == [
        "plugin.install_requested",
        "plugin.installed",
        "plugin.upgrade_requested",
        "plugin.upgraded",
    ]
    assert env.audit.entries[-1]["extra_data"]["new_permissions"] == ["db_write"]
