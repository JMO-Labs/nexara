"""
@file test_plugin_visibility.py
@brief Bots see over REST and webhooks exactly what REST visibility allows: never NSFW,
       never unrevealed answers, never groups they are not in (humans: groups likewise).
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch

from app.core.dependencies import get_current_user
from app.models.media import Media
from app.models.post import Post
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.plugins.events import dispatch_plugin_event
from tests.integration.api import test_plugins_api as pa

CID, _enable, _install, _user = pa.CID, pa._enable, pa._install, pa._user
session, env, _no_pubsub = pa.session, pa.env, pa._no_pubsub  # shared fixtures

SCOPES = ("posts:read", "comments:read")


async def _post(s, author: User, **kw) -> Post:
    p = Post(community_id=CID, author_id=author.id, content=kw.pop("content", "c"), **kw)
    s.add(p)
    await s.flush()
    return p


async def _media(s, author: User, nsfw: bool) -> Media:
    m = Media(
        community_id=CID,
        uploader_id=author.id,
        filename="f",
        content_type="image/png",
        storage_key=f"k/{uuid.uuid4()}",
        size_bytes=1,
        status="ready",
        is_nsfw=nsfw,
    )
    s.add(m)
    await s.flush()
    return m


async def _bot_client(e) -> tuple[User, dict[str, str]]:
    """@brief Install+enable; return the bot user and its token header."""
    await _install(e, SCOPES)
    r = await _enable(e)
    bot = await e.s.get(User, uuid.UUID(r.json()["bot_user_id"]))
    assert bot is not None
    e.app.dependency_overrides.pop(get_current_user)
    return bot, {"Authorization": f"Bearer {r.json()['credentials']['token']}"}


async def _group(s, *members: User) -> Subgroup:
    g = Subgroup(community_id=CID, name="Parents", slug=f"g-{uuid.uuid4().hex[:8]}")
    s.add(g)
    await s.flush()
    for m in members:
        s.add(SubgroupMember(community_id=CID, subgroup_id=g.id, user_id=m.id))
    await s.flush()
    return g


async def _dispatch(e, post: Post, author: User) -> list[dict]:
    delay = MagicMock()
    with patch("app.tasks.plugin_tasks.deliver_plugin_event.delay", delay):
        await dispatch_plugin_event(e.s, CID, post=post, comment=None, author=author)
    return [json.loads(c.args[2]) for c in delay.call_args_list]


# --- I3: ?subgroup_id= never bypasses visibility ----------------------------------------


async def test_non_member_cannot_read_group_feed_by_id(env):
    teen = await _user(env.s, "member")
    g = await _group(env.s, env.u.member)
    p = await _post(env.s, env.u.member, subgroup_id=g.id, visibility="subgroup")
    env.who["u"] = teen
    r = await env.c.get(f"/api/v1/posts?subgroup_id={g.id}")
    assert r.status_code == 200 and r.json()["items"] == []
    env.who["u"] = env.u.member
    items = (await env.c.get(f"/api/v1/posts?subgroup_id={g.id}")).json()["items"]
    assert [i["id"] for i in items] == [str(p.id)]


async def test_bot_cannot_read_group_feed_by_id(env):
    _bot, h = await _bot_client(env)
    g = await _group(env.s, env.u.member)
    await _post(env.s, env.u.member, subgroup_id=g.id, visibility="subgroup")
    r = await env.c.get(f"/api/v1/posts?subgroup_id={g.id}", headers=h)
    assert r.status_code == 200 and r.json()["items"] == []
