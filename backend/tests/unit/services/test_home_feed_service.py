"""
@file test_home_feed_service.py
@brief Unit tests for HomeFeedService: merge, privacy, blocks, paging.

Fakes honor the repo contract (subgroup scoping, block filter, cursor) so the
service wiring is exercised end to end.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.user import User
from app.schemas.activity import ActivityFeedResponse, ActivityItem
from app.services.home_feed_service import HomeFeedService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
VIEWER_ID = uuid.uuid4()
SG_ID = uuid.uuid4()
BLOCKED_ID = uuid.uuid4()
T0 = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


def _post(offset: int, *, subgroup: uuid.UUID | None = None, author=None) -> dict:
    return {
        "id": uuid.uuid4(),
        "created_at": T0 - timedelta(minutes=offset),
        "subgroup_id": subgroup,
        "author_id": author or uuid.uuid4(),
    }


def _act(offset: int, verb="post.commented", *, subgroup=None, actor=None) -> dict:
    return {"offset": offset, "verb": verb, "subgroup": subgroup, "actor": actor}


def _item(a: dict) -> ActivityItem:
    return ActivityItem(
        id=uuid.uuid4(),
        actor_id=a["actor"] or uuid.uuid4(),
        actor_name="A",
        verb=a["verb"],
        object_type="post",
        object_id=uuid.uuid4(),
        count=1,
        created_at=T0 - timedelta(minutes=a["offset"]),
    )


def _service(posts: list[dict], acts: list[dict], member_of: list[uuid.UUID]):
    """Build service with fakes applying subgroup scoping, blocks and cursor."""

    async def list_feed(community_id, *, viewer_id, cursor, limit, subgroup_ids=None, **_):
        cur = datetime.fromisoformat(cursor) if cursor else None
        rows = [
            p
            for p in posts
            if p["author_id"] != BLOCKED_ID
            and (p["subgroup_id"] is None or p["subgroup_id"] in (subgroup_ids or []))
            and (cur is None or p["created_at"] < cur)
        ]
        rows.sort(key=lambda p: p["created_at"], reverse=True)
        more = len(rows) > limit
        rows = rows[:limit]
        return rows, (rows[-1]["created_at"].isoformat() if more else None)

    async def list_for_user(user, cursor=None, limit=30, window_seconds=3600, subgroup_ids=None):
        rows = [
            a
            for a in acts
            if a["actor"] != BLOCKED_ID
            and (a["subgroup"] is None or a["subgroup"] in (subgroup_ids or []))
            and (cursor is None or T0 - timedelta(minutes=a["offset"]) < cursor)
        ]
        rows.sort(key=lambda a: a["offset"])
        items = [_item(a) for a in rows[:limit]]
        return ActivityFeedResponse(items=items, next_cursor=None)

    post_repo = MagicMock()
    post_repo.list_feed = AsyncMock(side_effect=list_feed)
    activity = MagicMock()
    activity.list_for_user = AsyncMock(side_effect=list_for_user)
    member_repo = MagicMock()
    member_repo.list_my_roles = AsyncMock(return_value={s: "member" for s in member_of})
    svc = HomeFeedService(post_repo, activity, member_repo, COMMUNITY_ID)
    return svc, activity


def _viewer() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = VIEWER_ID
    return u


@pytest.mark.asyncio
async def test_merge_order_and_post_created_excluded():
    svc, activity = _service(
        [_post(1), _post(5)],
        [_act(3), _act(0, "post.created"), _act(7)],
        [],
    )
    res = await svc.list(_viewer(), None, 20)
    assert [i.kind for i in res.items] == ["post", "activity", "post", "activity"]
    assert all(i.created_at for i in res.items)
    assert activity.list_for_user.call_args.kwargs["window_seconds"] == 10
    assert res.next_cursor is None


@pytest.mark.asyncio
async def test_subgroup_items_hidden_from_non_member():
    sg_post, sg_act = _post(1, subgroup=SG_ID), _act(2, subgroup=SG_ID)
    svc, _ = _service([sg_post, _post(4)], [sg_act, _act(5)], [])
    res = await svc.list(_viewer(), None, 20)
    assert len(res.items) == 2
    svc, _ = _service([sg_post, _post(4)], [sg_act, _act(5)], [SG_ID])
    assert len((await svc.list(_viewer(), None, 20)).items) == 4


@pytest.mark.asyncio
async def test_blocked_actor_absent():
    svc, _ = _service([_post(1, author=BLOCKED_ID)], [_act(2, actor=BLOCKED_ID)], [])
    assert (await svc.list(_viewer(), None, 20)).items == []


@pytest.mark.asyncio
async def test_paging_returns_distinct_items():
    posts = [_post(i * 2) for i in range(3)]
    acts = [_act(i * 2 + 1) for i in range(2)]
    svc, _ = _service(posts, acts, [])
    seen: list[uuid.UUID] = []
    cursor = None
    for _ in range(6):
        res = await svc.list(_viewer(), cursor, 2)
        seen += [i.id for i in res.items]
        cursor = res.next_cursor
        if cursor is None:
            break
    assert len(seen) == 5
    assert len(set(seen)) == 5


@pytest.mark.asyncio
async def test_chat_verbs_dropped():
    svc, _ = _service([], [_act(1, "chat.posted"), _act(2)], [])
    res = await svc.list(_viewer(), None, 20)
    assert [i.activity.verb for i in res.items] == ["post.commented"]
