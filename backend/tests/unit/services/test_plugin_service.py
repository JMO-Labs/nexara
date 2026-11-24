"""
@file
@brief PluginService: install review, bot accounts, enable/disable, settings, prefs, uninstall.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.plugin import PluginCommunity, PluginInstall
from app.models.user import COMMUNITY_DEFAULT
from app.plugins.manifest import parse_manifest
from app.repositories.plugin_repo import PluginRepository
from app.repositories.user_repo import UserRepository
from app.schemas.plugin import IndexInstall, UrlInstall
from app.services.plugin_service import PluginService

CID = uuid.UUID(COMMUNITY_DEFAULT)
TOML = """
[plugin]
id = "dev.example.echo"
name = "Echo"
version = "1.0.0"
runtime = "node"
entrypoint = "index.js"
[bot]
display_name = "Echo Bot"
username = "echo"
[permissions]
scopes = ["posts:read", "comments:write"]
events = ["post.created"]
egress = ["api.example.com"]
[settings.api_key]
type = "secret"
label = "Key"
[settings.greeting]
type = "string"
label = "Greeting"
default = "hi"
[user_prefs.notify]
type = "boolean"
label = "Notify me"
"""
M = parse_manifest(TOML)


def _install() -> PluginInstall:
    return PluginInstall(
        id=uuid.uuid4(),
        plugin_id=M.id,
        version="1.0.0",
        manifest=M.model_dump(mode="json"),
        granted_scopes=list(M.scopes),
        status="running",
    )


def _body(scopes=None) -> UrlInstall:
    return UrlInstall(
        source="url",
        manifest_url="https://x.test/m.toml",
        endpoint_url="https://echo.test/events",
        approved_scopes=scopes if scopes is not None else list(M.scopes),
    )


@pytest.fixture
def env():
    repo = AsyncMock(spec=PluginRepository)
    users = AsyncMock(spec=UserRepository)
    audit = AsyncMock()
    users.username_exists.return_value = False
    users.try_create.side_effect = lambda u: u
    repo.get_install.return_value = None
    repo.get_community.return_value = None
    repo.create_install.side_effect = lambda **kw: PluginInstall(
        **{"id": uuid.uuid4(), "status": "running", **kw}
    )
    repo.upsert_community.side_effect = lambda pc: pc
    repo.get_user_pref.return_value = {}
    svc = PluginService(
        repo,
        users,
        CID,
        MagicMock(),
        Settings(SECRET_KEY="k"),
        audit_repo=audit,
        actor_id=uuid.uuid4(),
    )
    return svc, repo, users, audit


@pytest.fixture(autouse=True)
def _fetch():
    with patch("app.services.plugin_service.fetch_manifest_text", AsyncMock(return_value=TOML)):
        yield


async def test_install_requires_all_scopes_approved(env):
    svc, repo, _, _ = env
    with pytest.raises(AppError) as e:
        await svc.install(_body(["posts:read"]))
    assert e.value.code == "scopes_not_approved"
    assert e.value.details == {
        "scopes": M.scopes,
        "events": M.events,
        "egress": M.egress,
    }
    repo.create_install.assert_not_called()


async def test_install_ok_audited(env):
    svc, repo, _, audit = env
    out = await svc.install(_body())
    assert out.plugin_id == M.id and out.scopes == M.scopes
    assert audit.append.call_args.kwargs["action"] == "plugin.installed"


async def test_install_rejects_duplicate(env):
    svc, repo, _, _ = env
    repo.get_install.return_value = _install()
    with pytest.raises(AppError) as e:
        await svc.install(_body())
    assert e.value.code == "plugin_already_installed"
    repo.create_install.assert_not_called()


async def test_install_other_sources_not_supported(env):
    with pytest.raises(AppError) as e:
        await env[0].install(IndexInstall(source="index"))
    assert (e.value.code, e.value.status_code) == ("not_supported", 422)


@pytest.mark.parametrize(
    ("insecure", "host", "ok"),
    [
        (False, None, False),
        (True, None, True),
        (False, "http://echo:3000", True),
        (False, "http://other:3000", False),
    ],
)
async def test_install_http_endpoint_needs_flag_or_plugin_host(env, insecure, host, ok):
    from unittest.mock import MagicMock, patch

    s = MagicMock(PLUGINS_ALLOW_INSECURE_URLS=insecure, PLUGIN_HOST_URL=host)
    body = _body().model_copy(update={"endpoint_url": "http://echo:3000/events"})
    with (
        patch("app.plugins.fetch.get_settings", return_value=s),
        patch("app.services.plugin_service.fetch_manifest_text", AsyncMock(return_value=TOML)),
    ):
        if ok:
            await env[0].install(body)
        else:
            with pytest.raises(AppError) as e:
                await env[0].install(body)
            assert (e.value.code, e.value.status_code) == ("endpoint_insecure", 422)


async def test_install_bad_endpoint_scheme(env):
    body = _body().model_copy(update={"endpoint_url": "ftp://x"})
    with pytest.raises(AppError):
        await env[0].install(body)


async def test_enable_creates_bot_and_returns_credentials_once(env):
    svc, repo, users, audit = env
    repo.get_install.return_value = inst = _install()
    out = await svc.set_community(M.id, CID, enabled=True)
    bot = users.try_create.call_args.args[0]
    assert bot.is_bot and bot.role == "member" and bot.password_hash is None
    assert bot.email == f"echo+{inst.id}@plugins.invalid"
    assert bot.onboarding_done_at is not None
    assert out.credentials and out.credentials.token.startswith("nxp_")
    repo.add_token.assert_awaited_once()
    assert repo.add_token.call_args.args[2] != out.credentials.token  # hash only
    pc = repo.upsert_community.call_args.args[0]
    assert pc.webhook_secret != out.credentials.webhook_secret  # encrypted
    assert audit.append.call_args.kwargs["action"] == "plugin.enabled"
    # already enabled -> no new credentials
    repo.get_community.return_value = pc
    assert (await svc.set_community(M.id, CID, enabled=True)).credentials is None


async def test_username_collision_suffix(env):
    svc, repo, users, _ = env
    repo.get_install.return_value = _install()
    users.username_exists.side_effect = [True, True, False]
    await svc.set_community(M.id, CID, enabled=True)
    assert users.try_create.call_args.args[0].username == "echo-bot2"


async def test_reenable_reuses_bot_user(env):
    svc, repo, users, _ = env
    repo.get_install.return_value = inst = _install()
    bot = SimpleNamespace(id=uuid.uuid4(), is_active=False)
    users.get_by_id.return_value = bot
    repo.get_community.return_value = PluginCommunity(
        install_id=inst.id, community_id=CID, enabled=False, bot_user_id=bot.id, settings={}
    )
    out = await svc.set_community(M.id, CID, enabled=True)
    users.try_create.assert_not_called()
    assert bot.is_active is True and out.bot_user_id == bot.id and out.credentials


async def test_disable_revokes_and_deactivates_bot(env):
    svc, repo, users, audit = env
    repo.get_install.return_value = inst = _install()
    bot = SimpleNamespace(id=uuid.uuid4(), is_active=True)
    users.get_by_id.return_value = bot
    repo.get_community.return_value = PluginCommunity(
        install_id=inst.id, community_id=CID, enabled=True, bot_user_id=bot.id, settings={}
    )
    out = await svc.set_community(M.id, CID, enabled=False)
    repo.revoke_tokens.assert_awaited_once_with(inst.id, CID)
    assert bot.is_active is False and out.enabled is False and out.credentials is None
    assert audit.append.call_args.kwargs["action"] == "plugin.disabled"


@pytest.mark.parametrize("delete", [True, False])
async def test_uninstall_delete_content(env, delete):
    svc, repo, users, audit = env
    repo.get_install.return_value = inst = _install()
    bot_id = uuid.uuid4()
    users.get_by_id.return_value = SimpleNamespace(id=bot_id, is_active=True)
    repo.list_communities.return_value = [
        PluginCommunity(
            install_id=inst.id, community_id=CID, enabled=True, bot_user_id=bot_id, settings={}
        )
    ]
    await svc.uninstall(M.id, delete_content=delete)
    assert repo.soft_delete_bot_content.await_count == (1 if delete else 0)
    repo.delete_install.assert_awaited_once_with(inst.id)
    repo.revoke_tokens.assert_awaited()
    assert audit.append.call_args.kwargs["action"] == "plugin.uninstalled"


async def test_get_settings_masks_secrets_and_blank_keeps_existing(env):
    svc, repo, _, audit = env
    repo.get_install.return_value = inst = _install()
    pc = PluginCommunity(install_id=inst.id, community_id=CID, enabled=True, settings={})
    repo.get_community.return_value = pc
    out = await svc.update_settings(M.id, {"api_key": "s3cret", "greeting": "yo"})
    assert out == {"api_key": {"set": True}, "greeting": "yo"}
    assert "s3cret" not in str(out) and pc.settings["api_key"] != "s3cret"
    assert "s3cret" not in str(audit.append.call_args)
    before = pc.settings["api_key"]
    out = await svc.update_settings(M.id, {"api_key": ""})
    assert pc.settings["api_key"] == before and out["api_key"] == {"set": True}
    assert svc.decrypted_settings(pc, M)["api_key"] == "s3cret"
    assert (await svc.get_settings(M.id))["api_key"] == {"set": True}


async def test_update_settings_validates(env):
    svc, repo, _, _ = env
    repo.get_install.return_value = _install()
    with pytest.raises(AppError) as e:
        await svc.update_settings(M.id, {"nope": 1})
    assert e.value.code == "invalid_plugin_value"


async def test_user_prefs_default_off(env):
    svc, repo, _, _ = env
    repo.get_install.return_value = inst = _install()
    repo.get_community.return_value = PluginCommunity(
        install_id=inst.id, community_id=CID, enabled=True, settings={}
    )
    uid = uuid.uuid4()
    assert await svc.get_user_prefs(M.id, uid) == {"notify": False}
    assert await svc.set_user_prefs(M.id, uid, {"notify": True}) == {"notify": True}
    repo.set_user_pref.assert_awaited_once_with(inst.id, uid, CID, {"notify": True})
    with pytest.raises(AppError):
        await svc.set_user_prefs(M.id, uid, {"notify": "yes"})


async def test_age_suggestion_for_bot_not_found():
    from app.core.exceptions import NotFoundError
    from app.services.age_service import AgeService

    repo = AsyncMock()
    repo.get_user.return_value = SimpleNamespace(is_bot=True)
    svc = AgeService.__new__(AgeService)
    svc._repo, svc._cid, svc._actor = repo, CID, uuid.uuid4()
    with pytest.raises(NotFoundError):
        await svc.suggest(uuid.uuid4(), "adult", None)


async def test_notify_skips_bots():
    from app.services.notification_service import NotificationService

    svc = NotificationService.__new__(NotificationService)
    svc._settings_repo = AsyncMock()
    svc._settings_repo.user_tz_and_bot.return_value = (None, True)
    with patch("app.services.notification_service.registry") as reg:
        reg.get.return_value = MagicMock()
        assert await svc.notify(uuid.uuid4(), "system", {"message": "x"}) is None
    svc._settings_repo.get_or_create.assert_not_called()


@pytest.mark.parametrize("op", ["change_role", "restore_user"])
async def test_admin_refuses_bot_targets(op):
    from app.services.admin_service import AdminService

    svc = AdminService.__new__(AdminService)
    svc._community_id = CID
    svc._user_repo = AsyncMock()
    bot = SimpleNamespace(is_bot=True, role="member")
    svc._user_repo.get_by_id.return_value = bot
    svc._user_repo.get_by_id_include_deleted.return_value = bot
    args = (SimpleNamespace(id=uuid.uuid4()), uuid.uuid4())
    call = (
        svc.change_role(*args, "admin", None)
        if op == "change_role"
        else svc.restore_user(*args, None)
    )
    with pytest.raises(AppError) as e:
        await call
    assert (e.value.code, e.value.status_code) == ("bot_account", 422)


async def test_ui_lists_only_running_enabled_installs(env):
    svc, repo, _users, _audit = env
    repo.list_enabled_installs.return_value = [_install()]
    out = await svc.list_enabled_ui()
    assert [p.plugin_id for p in out] == [M.id]
    repo.list_enabled_installs.assert_awaited_once()
    repo.list_installs.assert_not_called()
