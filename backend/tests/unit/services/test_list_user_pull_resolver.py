"""@file Tests for UserPullResolver (privacy gating, batching, caching)."""

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.services.list_user_pull_resolver import UserPullResolver

LIST_ID = uuid.uuid4()
VIEWER = uuid.uuid4()
U1, U2 = uuid.uuid4(), uuid.uuid4()


def _pull(key, src):
    cfg = {"pull_from": src, "target_user_field": "who"}
    return {"key": key, "type": "user_pull", "config": cfg}


SCHEMA = [{"key": "who", "type": "user", "config": {}}, _pull("mail", "email")]
SCHEMA += [_pull("bday", "birthday"), _pull("tel", "phone")]


def _rows(rows):
    r = MagicMock()
    r.scalars.return_value.all.return_value = rows
    return r


def _setup(share: dict, prefs: dict):
    uid1, uid2 = U1, U2
    items = [
        SimpleNamespace(id=uuid.uuid4(), values={"who": str(uid1)}),
        SimpleNamespace(id=uuid.uuid4(), values={"who": str(uid2)}),
    ]
    users = [
        SimpleNamespace(id=uid1, email="a@x.io", birthday=date(2000, 1, 2)),
        SimpleNamespace(id=uid2, email="b@x.io", birthday=date(1999, 3, 4)),
    ]
    default = {"can_share_email": True, "show_birthday_to": "nobody"}
    sets = [SimpleNamespace(user_id=u, **prefs.get(u, default)) for u in (uid1, uid2)]
    session = AsyncMock()
    session.execute.side_effect = [_rows(items), _rows(users), _rows(sets)]
    members = AsyncMock()
    members.list_members.return_value = [
        SimpleNamespace(user_id=u, share_personal=share.get(u, False)) for u in (uid1, uid2)
    ]
    return items, session, members


async def test_resolve_gates_and_batches():
    items, session, members = _setup({U1: True}, {})
    out = await UserPullResolver().resolve(
        [i.id for i in items], LIST_ID, SCHEMA, VIEWER, members, session
    )
    assert out[items[0].id]["mail"] == "a@x.io"
    assert out[items[1].id]["mail"] is None  # share_personal off
    assert out[items[0].id]["bday"] is None  # pref restricts
    assert out[items[0].id]["tel"] is None  # no phone column: graceful
    assert session.execute.await_count == 3  # items, users, settings (one each)


async def test_pref_denied_returns_none():
    items, session, members = _setup(
        {U1: True, U2: True}, {U1: {"can_share_email": False}, U2: {"can_share_email": True}}
    )
    out = await UserPullResolver().resolve(
        [i.id for i in items], LIST_ID, SCHEMA, VIEWER, members, session
    )
    assert out[items[0].id]["mail"] is None
    assert out[items[1].id]["mail"] == "b@x.io"


async def test_viewer_sees_own_data_and_cache_reused():
    items, session, members = _setup({}, {U1: {"can_share_email": False}})
    r = UserPullResolver()
    out = await r.resolve([items[0].id], LIST_ID, SCHEMA, U1, members, session)
    assert out[items[0].id]["mail"] == "a@x.io"
    session.execute.side_effect = AssertionError("should be cached")
    await r.resolve([items[0].id], LIST_ID, SCHEMA, U1, members, session)


async def test_no_user_pull_fields_skips_queries():
    session = AsyncMock()
    r = UserPullResolver()
    out = await r.resolve([uuid.uuid4()], LIST_ID, [], VIEWER, AsyncMock(), session)
    assert out == {}
    session.execute.assert_not_called()
