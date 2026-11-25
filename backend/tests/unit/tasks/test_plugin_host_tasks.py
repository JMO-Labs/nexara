"""
@file test_plugin_host_tasks.py
@brief plugin-host poll: status sync, re-push on needs_config/stopped/missing, one alert.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import get_settings
from app.core.encryption import derive_fernet_key, encrypt_secret
from app.core.exceptions import AppError
from app.models.plugin import PluginCommunity, PluginInstall
from app.plugins.manifest import parse_manifest
from app.repositories.plugin_repo import PluginRepository
from app.services.plugin_host_client import HostPluginStatus, PluginHostClient
from app.tasks.celery_app import celery_app
from app.tasks.plugin_host_tasks import sync_installs

M = parse_manifest("""
[plugin]
id = "dev.example.echo"
name = "Echo"
version = "1.0.0"
runtime = "node"
entrypoint = "index.js"
[bot]
display_name = "Echo Bot"
username = "echo"
[settings.api_key]
type = "secret"
label = "Key"
""")
KEY = derive_fernet_key(get_settings().SECRET_KEY)
CID = uuid.UUID(get_settings().COMMUNITY_ID)


def _inst(status: str) -> PluginInstall:
    return PluginInstall(
        id=uuid.uuid4(),
        plugin_id=M.id,
        version="1.0.0",
        manifest=M.model_dump(mode="json"),
        package_url="https://x.test/p.tgz",
        sha256="a" * 64,
        status=status,
    )


@pytest.fixture
def env():
    inst = _inst("installing")
    repo = AsyncMock(spec=PluginRepository)
    repo.list_installs.return_value = [inst]
    repo.get_install.return_value = inst
    repo.list_communities.return_value = [
        PluginCommunity(
            install_id=inst.id,
            community_id=CID,
            enabled=True,
            bot_user_id=uuid.uuid4(),
            settings={"api_key": encrypt_secret("sekret", KEY)},
            webhook_secret=encrypt_secret("whsec", KEY),
        )
    ]
    client = AsyncMock(spec=PluginHostClient)
    session = MagicMock(commit=AsyncMock(), rollback=AsyncMock())
    alert = AsyncMock()
    with (
        patch("app.tasks.plugin_host_tasks.PluginRepository", return_value=repo),
        patch("app.tasks.plugin_host_tasks.admin_alert", alert),
    ):
        yield inst, repo, client, session, alert


def _rows(status: str, err: str | None = None):
    return [HostPluginStatus(id=M.id, version="1.0.0", status=status, last_error=err)]


async def test_running_flips_install(env):
    inst, _, client, session, _ = env
    client.status.return_value = _rows("running")
    await sync_installs(session, client)
    assert inst.status == "running"
    client.put.assert_not_called()
    session.commit.assert_awaited()


@pytest.mark.parametrize("rows", [[], _rows("needs_config"), _rows("stopped")])
async def test_repush_on_needs_config_stopped_or_missing(env, rows):
    inst, repo, client, session, _ = env
    client.status.return_value = rows
    await sync_installs(session, client)
    plugin_id, body = client.put.call_args.args
    assert plugin_id == M.id and body["sha256"] == "a" * 64
    env_ = body["env"]
    assert env_["NEXARA_WEBHOOK_SECRET"] == "whsec"
    assert env_["NEXARA_SETTINGS"] == {"api_key": "sekret"}
    assert env_["NEXARA_TOKEN"] == env_["NEXARA_COMMUNITIES"][0]["token"]
    assert "NEXARA_URL" not in env_
    json.dumps(body)  # serialisable
    repo.revoke_tokens.assert_awaited_with(inst.id, CID)
    repo.add_token.assert_awaited()


async def test_failed_alerts_once(env):
    inst, _, client, session, alert = env
    client.status.return_value = _rows("failed", "start_failed")
    await sync_installs(session, client)
    await sync_installs(session, client)
    assert inst.status == "failed"
    alert.assert_awaited_once()
    assert alert.call_args.args[2] == "plugin_failed"
    assert alert.call_args.args[3]["reason"] == "start_failed"


async def test_host_down_changes_nothing(env):
    inst, _, client, session, alert = env
    client.status.side_effect = AppError(code="plugin_host_unavailable", status_code=503)
    await sync_installs(session, client)
    assert inst.status == "installing"
    session.commit.assert_not_called()
    alert.assert_not_called()


async def test_repush_failure_rolls_back(env):
    inst, _, client, session, _ = env
    client.status.return_value = []
    client.put.side_effect = AppError(code="plugin_host_unavailable", status_code=503)
    await sync_installs(session, client)
    session.rollback.assert_awaited_once()
    session.commit.assert_not_called()


@pytest.mark.parametrize("status", ["running", "installing"])
async def test_disabled_everywhere_but_live_on_host_is_stopped(env, status):
    inst, repo, client, session, _ = env
    repo.list_communities.return_value[0].enabled = False
    client.status.return_value = _rows(status)
    await sync_installs(session, client)
    client.stop.assert_awaited_once_with(M.id)
    client.put.assert_not_called()


async def test_disabled_everywhere_and_stopped_on_host_is_left(env):
    _, repo, client, session, _ = env
    repo.list_communities.return_value[0].enabled = False
    client.status.return_value = _rows("stopped")
    await sync_installs(session, client)
    client.stop.assert_not_called()
    client.put.assert_not_called()


async def test_blocked_is_stopped(env):
    inst, _, client, session, _ = env
    inst.status = "blocked"
    client.status.return_value = _rows("running")
    await sync_installs(session, client)
    client.stop.assert_awaited_once_with(M.id)


async def test_stop_failure_is_quiet(env):
    _, repo, client, session, _ = env
    repo.list_communities.return_value[0].enabled = False
    client.status.return_value = _rows("running")
    client.stop.side_effect = AppError(code="plugin_host_unavailable", status_code=503)
    await sync_installs(session, client)  # no raise


async def test_host_plugin_unknown_to_nexara_is_deleted(env):
    _, repo, client, session, _ = env
    repo.list_installs.return_value = []
    client.status.return_value = [
        HostPluginStatus(id="dev.gone.x", status="running"),
        HostPluginStatus(id="dev.new.y", status="installing"),
    ]
    await sync_installs(session, client)
    client.delete.assert_awaited_once_with("dev.gone.x", purge=False)


def test_beat_entry():
    entry = celery_app.conf.beat_schedule["plugin-host-poll"]
    assert entry["task"] == "app.tasks.plugin_host_tasks.poll" and entry["schedule"] == 60.0
    route = celery_app.conf.task_routes["app.tasks.plugin_host_tasks.*"]
    assert route == {"queue": "maintenance"}
