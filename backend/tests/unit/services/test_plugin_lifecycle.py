"""@file test_plugin_lifecycle.py
@brief Unit tests for PluginLifecycleService staged install/upgrade flows.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.plugins import get_plugin_service
from app.core.exceptions import ConflictError, GoneError, NotFoundError, ValidationError
from app.models.plugin import Plugin
from app.repositories.plugin_key_repo import PluginApiKeyRepository
from app.repositories.plugin_repo import PluginRepository
from app.services.plugin_lifecycle import PluginLifecycleService, permission_diff

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _write(root, version="1.0.0", min_core="0.1.0", perms=("db_read",)):
    d = root / "hello"
    d.mkdir(exist_ok=True)
    (d / "__init__.py").write_text("")
    (d / "manifest.json").write_text(
        json.dumps(
            {
                "id": "hello",
                "name": "Hello",
                "version": version,
                "author": "a",
                "description": "d",
                "min_core_version": min_core,
                "permissions": list(perms),
            }
        )
    )


@pytest.fixture
def repo():
    r = AsyncMock(spec=PluginRepository)
    r.save.side_effect = lambda row: row
    return r


@pytest.fixture
def keys():
    return AsyncMock(spec=PluginApiKeyRepository)


@pytest.fixture
def svc(tmp_path, repo, keys):
    _write(tmp_path)
    return PluginLifecycleService(repo, keys, CID, tmp_path, "1.0.0")


def _installed(version="1.0.0", granted=()):
    row = MagicMock(spec=Plugin)
    row.id, row.version, row.deleted_at = "hello", version, None
    row.permissions_granted, row.pending_manifest = list(granted), None
    return row


def test_permission_diff():
    d = permission_diff(["b", "a"], ["b", "c"])
    assert d["new_permissions"] == ["a"] and d["removed_permissions"] == ["c"]
    assert d["permissions_requested"] == ["a", "b"]


async def test_request_install_stages_new_row(svc, repo):
    repo.get.side_effect = [None, None]
    review = await svc.request_install("hello")
    row = repo.save.call_args.args[0]
    assert row.is_enabled is False and row.deleted_at is not None
    assert row.pending_manifest["kind"] == "install"
    assert review["new_permissions"] == ["db_read"]


async def test_request_install_reuses_soft_deleted_row(svc, repo):
    old = _installed()
    repo.get.side_effect = [None, old]
    await svc.request_install("hello")
    assert repo.save.call_args.args[0] is old
    assert old.pending_manifest["kind"] == "install"


async def test_request_install_conflicts_when_installed(svc, repo):
    repo.get.return_value = _installed()
    with pytest.raises(ConflictError):
        await svc.request_install("hello")


async def test_request_install_incompatible_core(tmp_path, repo, keys):
    _write(tmp_path, min_core="9.0.0")
    s = PluginLifecycleService(repo, keys, CID, tmp_path, "1.0.0")
    with pytest.raises(ValidationError):
        await s.request_install("hello")


async def test_confirm_install_activates_and_issues_key(svc, repo, keys):
    repo.get.side_effect = [None, None]
    await svc.request_install("hello")
    staged = repo.save.call_args.args[0]
    repo.get.side_effect = None
    repo.get.return_value = staged
    row, plain, perms = await svc.confirm_install("hello")
    assert row.is_enabled and row.deleted_at is None and row.pending_manifest is None
    assert perms == ["db_read"] and plain.startswith("nxr_plugin_hello_")
    assert keys.create.call_args.kwargs["key_hint"] == plain[-4:]


async def test_confirm_install_already_installed(svc, repo):
    repo.get.return_value = _installed()
    with pytest.raises(ConflictError):
        await svc.confirm_install("hello")


async def test_confirm_install_without_stage_404(svc, repo):
    repo.get.return_value = None
    with pytest.raises(NotFoundError):
        await svc.confirm_install("hello")


async def test_confirm_install_wrong_kind_404(svc, repo):
    row = _installed()
    row.deleted_at = datetime.now(UTC)
    row.pending_manifest = {"kind": "upgrade", "staged_at": datetime.now(UTC).isoformat()}
    repo.get.return_value = row
    with pytest.raises(NotFoundError):
        await svc.confirm_install("hello")


async def test_confirm_install_expired_410(svc, repo):
    row = _installed()
    row.deleted_at = datetime.now(UTC)
    old = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    row.pending_manifest = {"kind": "install", "staged_at": old, "manifest": {}}
    repo.get.return_value = row
    with pytest.raises(GoneError) as e:
        await svc.confirm_install("hello")
    assert e.value.status_code == 410 and e.value.code == "GONE"


async def test_confirm_install_manifest_changed(svc, repo, tmp_path):
    repo.get.side_effect = [None, None]
    await svc.request_install("hello")
    staged = repo.save.call_args.args[0]
    repo.get.side_effect = None
    repo.get.return_value = staged
    _write(tmp_path, perms=("db_read", "db_write"))
    with pytest.raises(ConflictError):
        await svc.confirm_install("hello")


async def test_gone_error_default_message():
    assert GoneError().message


async def test_request_upgrade_returns_diff(svc, repo, tmp_path):
    _write(tmp_path, version="1.1.0", perms=("db_write",))
    row = _installed(granted=["db_read"])
    repo.get.return_value = row
    out = await svc.request_upgrade("hello")
    assert out["current_version"] == "1.0.0" and out["new_version"] == "1.1.0"
    assert out["new_permissions"] == ["db_write"]
    assert out["removed_permissions"] == ["db_read"]
    assert row.pending_manifest["kind"] == "upgrade"


async def test_request_upgrade_not_installed(svc, repo):
    repo.get.return_value = None
    with pytest.raises(NotFoundError):
        await svc.request_upgrade("hello")


async def test_request_upgrade_requires_newer_version(svc, repo):
    repo.get.return_value = _installed("1.0.0")
    with pytest.raises(ValidationError):
        await svc.request_upgrade("hello")


async def test_request_upgrade_incompatible_core(svc, repo, tmp_path):
    _write(tmp_path, version="2.0.0", min_core="9.0.0")
    repo.get.return_value = _installed()
    with pytest.raises(ValidationError):
        await svc.request_upgrade("hello")


async def test_confirm_upgrade_applies(svc, repo, tmp_path):
    _write(tmp_path, version="1.1.0", perms=("db_write",))
    row = _installed(granted=["db_read"])
    repo.get.return_value = row
    await svc.request_upgrade("hello")
    row, diff = await svc.confirm_upgrade("hello")
    assert row.version == "1.1.0" and row.permissions_granted == ["db_write"]
    assert row.pending_manifest is None and diff["new_permissions"] == ["db_write"]


async def test_confirm_upgrade_without_stage(svc, repo):
    repo.get.return_value = _installed()
    with pytest.raises(NotFoundError):
        await svc.confirm_upgrade("hello")


async def test_confirm_upgrade_manifest_changed(svc, repo, tmp_path):
    _write(tmp_path, version="1.1.0")
    repo.get.return_value = _installed()
    await svc.request_upgrade("hello")
    _write(tmp_path, version="1.2.0")
    with pytest.raises(ConflictError):
        await svc.confirm_upgrade("hello")


def test_get_plugin_service_builds_lifecycle_service():
    settings = MagicMock(COMMUNITY_ID=str(CID), APP_VERSION="1.0.0")
    assert isinstance(get_plugin_service(MagicMock(), settings), PluginLifecycleService)
