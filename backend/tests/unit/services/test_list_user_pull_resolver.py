"""@file Tests for UserPullResolver (privacy gating, batching, caching)."""

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from app.models.list import ListItem, ListMember
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_member_repo import ListMemberRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.user_repo import UserRepository
from app.services.list_user_pull_resolver import UserPullRepos, UserPullResolver

LIST_ID = uuid.uuid4()
CID = uuid.uuid4()
VIEWER = uuid.uuid4()
U1, U2 = uuid.uuid4(), uuid.uuid4()


def _pull(key, src):
    cfg = {"pull_from": src, "target_user_field": "who"}
    return {"key": key, "type": "user_pull", "config": cfg}


SCHEMA = [{"key": "who", "type": "user", "config": {}}, _pull("mail", "email")]
SCHEMA += [_pull("bday", "birthday"), _pull("tel", "phone")]


def _mock(spec, **kw):
    m = MagicMock(spec=spec)
    for k, v in kw.items():
        setattr(m, k, v)
    return m


def _settings(uid, profile="community", bday="nobody"):
    return _mock(UserSettings, user_id=uid, profile_visible_to=profile, show_birthday_to=bday)


def _setup(share: dict, prefs: dict | None = None):
    """@brief Repos mocked with spec; prefs maps uid -> UserSettings mock (absent = no row)."""
    items = [_mock(ListItem, id=uuid.uuid4(), values={"who": str(u)}) for u in (U1, U2)]
    users = [
        _mock(User, id=U1, email="a@x.io", birthday=date(2000, 1, 2)),
        _mock(User, id=U2, email="b@x.io", birthday=date(1999, 3, 4)),
    ]
    if prefs is None:
        prefs = {U1: _settings(U1), U2: _settings(U2)}
    repos = UserPullRepos(
        items=AsyncMock(spec=ListItemRepository),
        users=AsyncMock(spec=UserRepository),
        settings=AsyncMock(spec=SettingsRepository),
        members=AsyncMock(spec=ListMemberRepository),
    )
    repos.items.get_many.return_value = items
    repos.users.get_many.return_value = users
    repos.settings.get_many.return_value = list(prefs.values())
    repos.members.list_members.return_value = [
        _mock(ListMember, user_id=u, share_personal=share.get(u, False)) for u in (U1, U2)
    ]
    return items, repos


async def _resolve(r, items, repos, viewer=VIEWER):
    return await r.resolve([i.id for i in items], LIST_ID, SCHEMA, viewer, CID, repos)


async def test_resolve_gates_and_batches():
    items, repos = _setup({U1: True})
    out = await _resolve(UserPullResolver(), items, repos)
    assert out[items[0].id]["mail"] == "a@x.io"
    assert out[items[1].id]["mail"] is None  # share_personal off
    assert out[items[0].id]["bday"] is None  # show_birthday_to=nobody
    assert out[items[0].id]["tel"] is None  # no phone column: graceful
    repos.users.get_many.assert_awaited_once()
    repos.settings.get_many.assert_awaited_once()


async def test_repos_receive_community_and_viewer():
    items, repos = _setup({U1: True})
    await _resolve(UserPullResolver(), items, repos)
    assert repos.items.get_many.await_args.args[2] == CID
    uargs = repos.users.get_many.await_args
    assert uargs.args[1] == CID and uargs.kwargs["viewer_id"] == VIEWER
    assert repos.settings.get_many.await_args.args[1] == CID


async def test_profile_private_hides_email():
    prefs = {U1: _settings(U1, profile="private"), U2: _settings(U2)}
    items, repos = _setup({U1: True, U2: True}, prefs)
    out = await _resolve(UserPullResolver(), items, repos)
    assert out[items[0].id]["mail"] is None
    assert out[items[1].id]["mail"] == "b@x.io"


async def test_missing_settings_row_defaults_to_community():
    items, repos = _setup({U1: True}, prefs={})
    out = await _resolve(UserPullResolver(), items, repos)
    assert out[items[0].id]["mail"] == "a@x.io"
    assert out[items[0].id]["bday"] == date(2000, 1, 2)


async def test_admin_only_birthday_denied():
    items, repos = _setup({U1: True}, {U1: _settings(U1, bday="admin_only")})
    out = await _resolve(UserPullResolver(), items, repos)
    assert out[items[0].id]["bday"] is None


async def test_community_birthday_allowed():
    items, repos = _setup({U1: True}, {U1: _settings(U1, bday="community")})
    out = await _resolve(UserPullResolver(), items, repos)
    assert out[items[0].id]["bday"] == date(2000, 1, 2)


async def test_viewer_sees_own_data_and_cache_reused():
    items, repos = _setup({}, {U1: _settings(U1, profile="private")})
    r = UserPullResolver()
    out = await _resolve(r, items[:1], repos, viewer=U1)
    assert out[items[0].id]["mail"] == "a@x.io"
    repos.items.get_many.side_effect = AssertionError("should be cached")
    await _resolve(r, items[:1], repos, viewer=U1)


async def test_cache_expires_after_ttl(monkeypatch):
    import app.services.list_user_pull_resolver as mod

    now = [100.0]
    monkeypatch.setattr(mod.time, "monotonic", lambda: now[0])
    items, repos = _setup({U1: True})
    r = UserPullResolver(cache_ttl=10)
    await _resolve(r, items, repos)
    now[0] += 11
    await _resolve(r, items, repos)
    assert repos.items.get_many.await_count == 2


async def test_no_user_pull_fields_skips_queries():
    items, repos = _setup({})
    out = await UserPullResolver().resolve([uuid.uuid4()], LIST_ID, [], VIEWER, CID, repos)
    assert out == {}
    repos.items.get_many.assert_not_called()


async def test_missing_or_blocked_user_resolves_none():
    items, repos = _setup({U1: True})
    repos.users.get_many.return_value = []  # filtered out (blocked/deleted/other community)
    out = await _resolve(UserPullResolver(), items[:1], repos)
    assert out[items[0].id]["mail"] is None
