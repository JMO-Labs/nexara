"""@file test_plugin_service.py
@brief Unit tests for PluginService lifecycle, settings and upgrade.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.plugin import Plugin
from app.repositories.plugin_key_repo import PluginApiKeyRepository
from app.repositories.plugin_repo import PluginRepository
from app.services.plugin_service import PluginService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _write(root, pid="hello", version="1.0.0", min_core="0.1.0", settings=None):
    d = root / pid
    d.mkdir(exist_ok=True)
    (d / "__init__.py").write_text("")
    (d / "manifest.json").write_text(
        json.dumps(
            {
                "id": pid,
                "name": "Hello",
                "version": version,
                "author": "a",
                "description": "d",
                "min_core_version": min_core,
                "settings": settings or {"greeting": {"type": "string", "label": "G"}},
            }
        )
    )


def _row(version="1.0.0", enabled=False):
    row = MagicMock(spec=Plugin)
    row.id, row.community_id, row.version = "hello", CID, version
    row.is_enabled, row.settings, row.deleted_at = enabled, {}, None
    return row


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
    return PluginService(repo, keys, CID, tmp_path, "1.0.0")


async def test_install_creates_entry_and_key(svc, repo, keys):
    repo.get.return_value = None
    row, plain = await svc.install("hello")
    assert row.id == "hello" and row.community_id == CID and not row.is_enabled
    assert plain.startswith("nxr_plugin_hello_")
    keys.create.assert_awaited_once()


async def test_install_twice_conflicts(svc, repo):
    repo.get.return_value = _row()
    with pytest.raises(ConflictError):
        await svc.install("hello")


async def test_uninstall_soft_deletes_and_revokes(svc, repo, keys):
    repo.get.return_value = _row(enabled=True)
    row = await svc.uninstall("hello")
    assert row.deleted_at is not None and row.is_enabled is False
    keys.revoke_all.assert_awaited_once_with("hello", CID)


async def test_uninstall_missing_not_found(svc, repo):
    repo.get.return_value = None
    with pytest.raises(NotFoundError):
        await svc.uninstall("hello")


async def test_enable_disable_toggle(svc, repo):
    repo.get.return_value = _row()
    assert (await svc.set_enabled("hello", True)).is_enabled is True
    assert (await svc.set_enabled("hello", False)).is_enabled is False
    repo.get.assert_awaited_with("hello", CID)


async def test_settings_validation(svc, repo):
    repo.get.return_value = _row()
    out = await svc.update_settings("hello", {"greeting": "hi"})
    assert out == {"greeting": "hi"}
    with pytest.raises(ValidationError):
        await svc.update_settings("hello", {"greeting": 5})
    with pytest.raises(ValidationError):
        await svc.update_settings("hello", {"nope": "x"})


async def test_upgrade_updates_version(tmp_path, repo, keys):
    _write(tmp_path, version="1.1.0")
    svc = PluginService(repo, keys, CID, tmp_path, "1.0.0")
    repo.get.return_value = _row("1.0.0")
    row = await svc.upgrade("hello", "1.1.0")
    assert row.version == "1.1.0"


async def test_upgrade_rejects_version_mismatch(svc, repo):
    repo.get.return_value = _row("0.9.0")
    with pytest.raises(ValidationError):
        await svc.upgrade("hello", "2.0.0")  # disk has 1.0.0


async def test_upgrade_rejects_downgrade_and_same(svc, repo):
    repo.get.return_value = _row("1.0.0")
    with pytest.raises(ValidationError):
        await svc.upgrade("hello", "1.0.0")


async def test_upgrade_rejects_incompatible_core(tmp_path, repo, keys):
    _write(tmp_path, version="2.0.0", min_core="9.0.0")
    svc = PluginService(repo, keys, CID, tmp_path, "1.0.0")
    repo.get.return_value = _row("1.0.0")
    with pytest.raises(ValidationError):
        await svc.upgrade("hello", "2.0.0")


async def test_upgrade_missing_not_found(svc, repo):
    repo.get.return_value = None
    with pytest.raises(NotFoundError):
        await svc.upgrade("hello", "1.1.0")
