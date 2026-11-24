"""
@file test_plugin_visibility.py
@brief Bots see over REST and webhooks exactly what REST visibility allows: never NSFW,
       never unrevealed answers, never groups they are not in (humans: groups likewise).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.core.dependencies import get_current_user
from app.models.media import Media
from app.models.post import Post, PostMedia
from app.models.prompt import Prompt, PromptPost
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


# --- I1: NSFW never reaches a bot -------------------------------------------------------


async def test_bot_token_cannot_read_nsfw_post_or_comments(env):
    _bot, h = await _bot_client(env)
    nsfw = await _post(env.s, env.u.member, is_nsfw=True)
    ok = await _post(env.s, env.u.member)
    assert (await env.c.get(f"/api/v1/posts/{nsfw.id}", headers=h)).status_code == 404
    assert (await env.c.get(f"/api/v1/posts/{nsfw.id}/comments", headers=h)).status_code == 404
    assert (await env.c.get(f"/api/v1/posts/{ok.id}", headers=h)).status_code == 200
    ids = {i["id"] for i in (await env.c.get("/api/v1/posts?limit=50", headers=h)).json()["items"]}
    assert str(nsfw.id) not in ids and str(ok.id) in ids


async def test_human_feed_nsfw_unchanged(env):
    nsfw = await _post(env.s, env.u.owner, is_nsfw=True)
    env.who["u"] = env.u.member
    assert (await env.c.get(f"/api/v1/posts/{nsfw.id}")).status_code == 200


async def test_bot_feed_hides_nsfw_media(env):
    _bot, h = await _bot_client(env)
    p = await _post(env.s, env.u.member)
    good, bad = await _media(env.s, env.u.member, False), await _media(env.s, env.u.member, True)
    env.s.add_all(
        [
            PostMedia(post_id=p.id, media_id=good.id, position=0),
            PostMedia(post_id=p.id, media_id=bad.id, position=1),
        ]
    )
    await env.s.flush()
    body = (await env.c.get(f"/api/v1/posts/{p.id}", headers=h)).json()
    assert [m["id"] for m in body["media"]] == [str(good.id)]


async def test_webhook_payload_omits_nsfw_media(env):
    await _bot_client(env)
    p = await _post(env.s, env.u.member)
    good, bad = await _media(env.s, env.u.member, False), await _media(env.s, env.u.member, True)
    env.s.add_all(
        [
            PostMedia(post_id=p.id, media_id=good.id, position=0),
            PostMedia(post_id=p.id, media_id=bad.id, position=1),
        ]
    )
    await env.s.flush()
    out = [b for b in await _dispatch(env, p, env.u.member) if b["event"] == "post.created"]
    assert len(out) == 1
    assert [m["id"] for m in out[0]["data"]["post"]["media"]] == [str(good.id)]


async def test_webhook_skips_nsfw_post(env):
    await _bot_client(env)
    p = await _post(env.s, env.u.member, is_nsfw=True)
    assert await _dispatch(env, p, env.u.member) == []


# --- I2: webhook visibility == REST visibility ------------------------------------------


async def test_unrevealed_daily_answer_not_pushed(env):
    await _bot_client(env)
    prompt = Prompt(
        community_id=CID, title="Q", body="Q?", frequency_type="daily", created_by=env.u.owner.id,
        prompt_type="daily_question", reveal_after_answer=True,
    )  # fmt: skip
    env.s.add(prompt)
    await env.s.flush()
    host = await _post(env.s, env.u.owner)
    pp = PromptPost(
        community_id=CID, prompt_id=prompt.id, post_id=host.id, fired_at=date.today(),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )  # fmt: skip
    env.s.add(pp)
    await env.s.flush()
    answer = await _post(env.s, env.u.member, reply_to_prompt_id=pp.id)
    assert await _dispatch(env, answer, env.u.member) == []


async def test_group_post_pushed_only_when_bot_is_member(env):
    bot, _h = await _bot_client(env)
    g = await _group(env.s, env.u.member)
    p = await _post(env.s, env.u.member, subgroup_id=g.id, visibility="subgroup")
    assert await _dispatch(env, p, env.u.member) == []
    env.s.add(SubgroupMember(community_id=CID, subgroup_id=g.id, user_id=bot.id))
    await env.s.flush()
    assert len(await _dispatch(env, p, env.u.member)) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"is_active": False},
        {"deleted_at": datetime.now(UTC)},
        {"is_bot": False},
        {"community_id": "other"},
    ],
)
async def test_no_webhook_for_dead_or_foreign_bot(env, change):
    bot, _h = await _bot_client(env)
    p = await _post(env.s, env.u.member)
    assert len(await _dispatch(env, p, env.u.member)) == 1
    for k, v in change.items():
        setattr(bot, k, env.u.other_admin.community_id if v == "other" else v)
    await env.s.flush()
    assert await _dispatch(env, p, env.u.member) == []


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
