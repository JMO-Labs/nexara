"""
@file test_plugin_service_package.py
@brief PluginService package mode: verify, hand to the plugin host, push env, uninstall.
"""

from __future__ import annotations

import logging
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.plugin import PluginCommunity, PluginInstall
from app.models.user import COMMUNITY_DEFAULT
from app.repositories.plugin_repo import PluginRepository
from app.repositories.user_repo import UserRepository
from app.schemas.plugin import PackageInstall
from app.services.plugin_host_client import HostPluginStatus, PluginHostClient
from app.services.plugin_service import PluginService
from tests.unit.services.test_plugin_service import M

CID = uuid.UUID(COMMUNITY_DEFAULT)
SHA = "b" * 64
HOST = "http://plugin-host:8700"


def _body(scopes=None) -> PackageInstall:
    return PackageInstall(
        source="package",
        package_url="https://x.test/echo-1.0.0.tgz",
        sha256=SHA,
        approved_scopes=scopes if scopes is not None else list(M.scopes),
    )


@pytest.fixture
def env():
    store: dict[str, PluginInstall] = {}
    comms: dict[uuid.UUID, PluginCommunity] = {}
    repo = AsyncMock(spec=PluginRepository)
    users = AsyncMock(spec=UserRepository)
    users.username_exists.return_value = False
    users.try_create.side_effect = lambda u: (setattr(u, "id", uuid.uuid4()), u)[1]
    repo.get_install.side_effect = lambda pid: store.get(pid)

    def create(**kw):
        inst = PluginInstall(id=uuid.uuid4(), **kw)
        store[inst.plugin_id] = inst
        return inst

    repo.create_install.side_effect = create
    repo.list_installs.side_effect = lambda: list(store.values())
    repo.get_community.side_effect = lambda iid, cid: comms.get(cid)

    def upsert(pc):
        comms[pc.community_id] = pc
        return pc

    repo.upsert_community.side_effect = upsert
    repo.list_communities.side_effect = lambda iid: list(comms.values())
    host = AsyncMock(spec=PluginHostClient)
    svc = PluginService(
        repo,
        users,
        CID,
        MagicMock(),
        Settings(SECRET_KEY="k", PLUGIN_HOST_URL=HOST, PLUGIN_HOST_SECRET="hs"),
        audit_repo=AsyncMock(),
    )
    fetch = AsyncMock(return_value=M)
    with (
        patch("app.services.plugin_host_ops.fetch_package_manifest", fetch),
        patch.object(PluginHostClient, "from_settings", return_value=host),
    ):
        yield svc, repo, host, fetch, store


async def test_not_configured_is_422_before_download(env):
    svc, repo, _, fetch, _ = env
    svc._settings = Settings(SECRET_KEY="k", PLUGIN_HOST_URL="")
    with pytest.raises(AppError) as e:
        await svc.install(_body())
    assert (e.value.code, e.value.status_code) == ("plugin_host_not_configured", 422)
    fetch.assert_not_called()


async def test_sha_mismatch_persists_nothing(env):
    svc, repo, host, fetch, _ = env
    fetch.side_effect = AppError(code="package_sha256_mismatch", status_code=422)
    with pytest.raises(AppError) as e:
        await svc.install(_body())
    assert e.value.code == "package_sha256_mismatch"
    repo.create_install.assert_not_called()
    host.put.assert_not_called()


async def test_scopes_review_before_persist(env):
    svc, repo, host, _, _ = env
    with pytest.raises(AppError) as e:
        await svc.install(_body([]))
    assert e.value.code == "scopes_not_approved"
    repo.create_install.assert_not_called()


async def test_install_records_only(env):
    svc, repo, host, fetch, _ = env
    out = await svc.install(_body())
    fetch.assert_awaited_once_with("https://x.test/echo-1.0.0.tgz", SHA)
    kw = repo.create_install.call_args.kwargs
    assert kw["endpoint_url"] == f"{HOST}/plugins/{M.id}/events" and kw["sha256"] == SHA
    assert out.status == "disabled" and out.source == "package" and not out.enabled
    repo.upsert_community.assert_not_called()
    repo.add_token.assert_not_called()
    host.put.assert_not_called()


async def _enabled(svc, host):
    await svc.install(_body())
    r = await svc.set_community(M.id, CID, enabled=True)
    return r, host.put.call_args.args


async def test_first_enable_pushes_one_token(env):
    svc, repo, host, _, store = env
    r, (pid, body) = await _enabled(svc, host)
    assert r.enabled and r.credentials is None and r.host_error is None
    assert pid == M.id and (body["runtime"], body["entrypoint"]) == ("node", "index.js")
    comm = body["env"]["NEXARA_COMMUNITIES"][0]
    assert comm["community_id"] == str(CID) and comm["bot_user_id"]
    assert body["env"]["NEXARA_TOKEN"] == comm["token"]
    assert repo.add_token.await_count == 1  # no issue-then-revoke
    repo.lock_install.assert_awaited_with(store[M.id].id)
    assert store[M.id].status == "installing"


async def test_reenable_is_noop(env):
    svc, repo, host, _, _ = env
    await _enabled(svc, host)
    host.put.reset_mock()
    await svc.set_community(M.id, CID, enabled=True)
    host.put.assert_not_called()
    assert repo.add_token.await_count == 1


async def test_settings_push_decrypted_never_logged(env, caplog, capsys):
    svc, _, host, _, _ = env
    caplog.set_level(logging.DEBUG)
    _, (_, first) = await _enabled(svc, host)
    r = await svc.set_community(M.id, CID, settings={"api_key": "sekret-value"})
    assert r.credentials is None
    body = host.put.call_args.args[1]
    assert body["env"]["NEXARA_SETTINGS"]["api_key"] == "sekret-value"
    assert body["env"]["NEXARA_TOKEN"] != first["env"]["NEXARA_TOKEN"]  # fresh per push
    assert "sekret-value" not in caplog.text and body["env"]["NEXARA_TOKEN"] not in caplog.text
    out = capsys.readouterr()
    assert "sekret-value" not in out.out + out.err


async def test_settings_while_disabled_no_push(env):
    svc, _, host, _, _ = env
    await svc.install(_body())
    await svc.set_community(M.id, CID, settings={"api_key": "x"})
    host.put.assert_not_called()


async def test_host_down_on_enable_is_503(env):
    svc, _, host, _, _ = env
    await svc.install(_body())
    host.put.side_effect = AppError(code="plugin_host_unavailable", status_code=503)
    with pytest.raises(AppError) as e:
        await svc.set_community(M.id, CID, enabled=True)
    assert (e.value.code, e.value.status_code) == ("plugin_host_unavailable", 503)


async def test_enable_without_host_is_422(env):
    svc, _, host, _, _ = env
    await svc.install(_body())
    svc._settings = Settings(SECRET_KEY="k", PLUGIN_HOST_URL="")
    with pytest.raises(AppError) as e:
        await svc.set_community(M.id, CID, enabled=True)
    assert e.value.code == "plugin_host_not_configured"


async def test_disable_last_community_stops(env):
    svc, repo, host, _, store = env
    await _enabled(svc, host)
    host.put.reset_mock()
    r = await svc.set_community(M.id, CID, enabled=False)
    host.stop.assert_awaited_once_with(M.id)
    host.put.assert_not_called()
    assert store[M.id].status == "disabled" and r.host_error is None


async def test_disable_with_host_down_still_revokes(env):
    svc, repo, host, _, store = env
    await _enabled(svc, host)
    host.stop.side_effect = AppError(code="plugin_host_unavailable", status_code=503)
    r = await svc.set_community(M.id, CID, enabled=False)
    assert not r.enabled and r.host_error == "unreachable"
    repo.revoke_tokens.assert_awaited_with(store[M.id].id, CID)


async def test_uninstall_host_down_still_removes(env):
    svc, repo, host, _, _ = env
    await _enabled(svc, host)
    host.delete.side_effect = AppError(code="plugin_host_unavailable", status_code=503)
    assert await svc.uninstall(M.id, delete_content=True) == "unreachable"
    repo.delete_install.assert_awaited_once()
    host.delete.assert_awaited_with(M.id, purge=True)


async def test_uninstall_cleanup_failed_keeps_disabled_install(env):
    svc, repo, host, _, store = env
    await _enabled(svc, host)
    repo.revoke_tokens.reset_mock()
    host.delete.side_effect = AppError(code="plugin_host_cleanup_failed", status_code=503)
    assert await svc.uninstall(M.id) == "cleanup_failed"
    repo.delete_install.assert_not_called()
    repo.revoke_tokens.assert_awaited()
    assert store[M.id].status == "disabled"
    host.delete.side_effect = None
    assert await svc.uninstall(M.id) is None
    repo.delete_install.assert_awaited_once()


async def test_list_shows_host_status(env):
    svc, _, host, _, _ = env
    await svc.install(_body())
    host.status.return_value = [
        HostPluginStatus(id=M.id, status="sandbox_unavailable", last_error="sandbox_unavailable")
    ]
    [p] = await svc.list_installed()
    assert (p.host_status, p.host_error) == ("sandbox_unavailable", "sandbox_unavailable")
    host.status.side_effect = AppError(code="plugin_host_unavailable", status_code=503)
    [p] = await svc.list_installed()
    assert p.host_status == "unreachable"


async def test_logs(env):
    svc, _, host, _, _ = env
    await svc.install(_body())
    host.logs.return_value = ["[x] hi"]
    assert await svc.logs(M.id, 10) == ["[x] hi"]
    host.logs.assert_awaited_with(M.id, 10)
