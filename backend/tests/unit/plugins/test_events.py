"""
@file test_events.py
@brief Which plugins get a webhook, and what the payload holds.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.plugins.events import dispatch_plugin_event

CID = uuid.uuid4()
BOT = uuid.uuid4()
AUTHOR_ID = uuid.uuid4()
MANIFEST = {
    "id": "com.example.echo",
    "name": "Echo",
    "version": "1.0.0",
    "runtime": "node",
    "entrypoint": "i.js",
    "bot_username": "echo",
    "bot_display_name": "Echo",
    "scopes": ["posts:read", "comments:read"],
    "events": ["post.created", "comment.created", "mention"],
    "user_prefs": {
        "roast_level": {
            "type": "select",
            "label": "L",
            "options": ["off", "mild"],
            "default": "off",
        }
    },
}


def _post(**kw):
    d = dict(
        id=uuid.uuid4(),
        content="hello",
        visibility="community",
        subgroup_id=None,
        author_id=AUTHOR_ID,
        created_at=datetime.now(UTC),
        is_nsfw=False,
        plugin_flags={},
    )
    d.update(kw)
    return SimpleNamespace(**d)


def _comment(content="hi"):
    return SimpleNamespace(
        id=uuid.uuid4(), content=content, parent_id=None, created_at=datetime.now(UTC)
    )


def _author(is_bot=False):
    return SimpleNamespace(id=AUTHOR_ID, username="al", display_name="Al", is_bot=is_bot)


def _inst(scopes=("posts:read", "comments:read")):
    return SimpleNamespace(
        id=uuid.uuid4(),
        plugin_id="echo",
        manifest=MANIFEST,
        granted_scopes=list(scopes),
        endpoint_url="https://p.example/events",
    )


def _pc():
    return SimpleNamespace(bot_user_id=BOT, webhook_secret="enc")


async def _run(*, post=None, comment=None, author=None, audience=(BOT,), pref=None, inst=None):
    repo = MagicMock()
    repo.list_enabled_for_event = AsyncMock(
        side_effect=lambda cid, ev: [(inst or _inst(), _pc())] if ev in MANIFEST["events"] else []
    )
    repo.get_user_pref = AsyncMock(return_value=pref or {})
    repo.list_post_media = AsyncMock(return_value=[])
    delay = MagicMock()
    with (
        patch("app.plugins.events.PluginRepository", return_value=repo),
        patch("app.plugins.events.resolve_audience", AsyncMock(return_value=list(audience))),
        patch("app.tasks.plugin_tasks.deliver_plugin_event.delay", delay),
    ):
        await dispatch_plugin_event(
            MagicMock(), CID, post=post or _post(), comment=comment, author=author or _author()
        )
    return [(c.args[0], json.loads(c.args[2])) for c in delay.call_args_list]


async def test_post_created_enqueues():
    out = await _run()
    assert [b["event"] for _, b in out] == ["post.created"]
    assert out[0][0] == "https://p.example/events"
    assert out[0][1]["data"]["post"]["content"] == "hello"


async def test_comment_created_has_comment_data():
    out = await _run(comment=_comment())
    assert out[0][1]["event"] == "comment.created"
    assert out[0][1]["data"]["comment"]["content"] == "hi"


@pytest.mark.parametrize(
    "kw",
    [
        {"author": _author(is_bot=True)},
        {"post": _post(visibility="private")},
        {"post": _post(visibility="subgroup", subgroup_id=uuid.uuid4()), "audience": ()},
        {"audience": ()},  # blocked author: resolve_audience drops the bot
        {"post": _post(is_nsfw=True)},
        {"inst": _inst(scopes=("comments:read",))},
    ],
)
async def test_not_dispatched(kw):
    assert await _run(**kw) == []


async def test_mention_event_when_bot_username_mentioned():
    out = await _run(post=_post(content="hey @echo look"))
    assert [b["event"] for _, b in out] == ["post.created", "mention"]


async def test_payload_author_prefs_defaults_off():
    out = await _run()
    assert out[0][1]["data"]["author_prefs"] == {"roast_level": "off"}


async def test_payload_includes_flags_slice():
    out = await _run(post=_post(plugin_flags={"echo": {"roast_me": True}, "other": {"x": 1}}))
    assert out[0][1]["data"]["flags"] == {"roast_me": True}


async def test_dispatch_error_swallowed():
    with patch("app.plugins.events.PluginRepository", side_effect=RuntimeError("boom")):
        await dispatch_plugin_event(MagicMock(), CID, post=_post(), comment=None, author=_author())
