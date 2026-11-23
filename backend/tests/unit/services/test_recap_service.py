"""
@file test_recap_service.py
@brief Unit tests: recap_due, user-local dispatch idempotency, build and sections.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.community import Community
from app.models.user import User
from app.repositories.recap_repo import RecapCandidate
from app.services import recap_sections
from app.services.recap_service import RecapService, recap_due

CID = uuid.uuid4()
SUN = datetime(2026, 11, 22, 8, 30, tzinfo=UTC)  # a Sunday


def test_weekly_due_sunday_8():
    assert recap_due("weekly", SUN, None)
    assert recap_due("weekly", SUN, SUN - timedelta(days=7))


def test_weekly_not_due_other_day_hour_recent_or_off():
    assert not recap_due("weekly", SUN - timedelta(days=1), None)
    assert not recap_due("weekly", SUN.replace(hour=9), None)
    assert not recap_due("weekly", SUN, SUN - timedelta(days=2))
    assert not recap_due("off", SUN, None)


def test_monthly():
    first = datetime(2026, 12, 1, 8, 0, tzinfo=UTC)
    assert recap_due("monthly", first, None)
    assert not recap_due("monthly", first, first - timedelta(days=20))
    assert not recap_due("monthly", first.replace(day=2), None)


def _comm(features=None):
    c = MagicMock(spec=Community)
    c.id = CID
    c.features = features or {}
    return c


def _svc(cands, features=None):
    svc = RecapService(MagicMock(), CID)
    svc._repo = AsyncMock()
    svc._repo.candidates.return_value = cands
    comm_repo = AsyncMock()
    comm_repo.get.return_value = _comm(features)
    return svc, comm_repo


async def test_honolulu_due_at_utc_sunday_1810_not_0810():
    uid = uuid.uuid4()
    cand = RecapCandidate(uid, "Pacific/Honolulu", None, "weekly", None)
    svc, comms = _svc([cand])
    with patch("app.services.recap_service.CommunityRepository", return_value=comms):
        due = await svc.due_user_ids(datetime(2026, 11, 22, 18, 10, tzinfo=UTC))
        early = await svc.due_user_ids(datetime(2026, 11, 22, 8, 10, tzinfo=UTC))
    assert due == [uid]
    assert early == []


async def test_due_stamps_so_second_run_finds_nobody():
    uid = uuid.uuid4()
    state = {"last": None}
    svc, comms = _svc([])

    async def cands(_cid):
        return [RecapCandidate(uid, None, None, "weekly", state["last"])]

    async def stamp(_uid, now):
        state["last"] = now

    svc._repo.candidates.side_effect = cands
    svc._repo.stamp_sent.side_effect = stamp
    with patch("app.services.recap_service.CommunityRepository", return_value=comms):
        assert await svc.due_user_ids(SUN) == [uid]
        assert await svc.due_user_ids(SUN + timedelta(minutes=1)) == []


async def test_flag_off_nobody_due_and_build_empty():
    svc, comms = _svc([RecapCandidate(uuid.uuid4(), None, None, "weekly", None)], {"recap": False})
    with patch("app.services.recap_service.CommunityRepository", return_value=comms):
        assert await svc.due_user_ids(SUN) == []
        assert await svc.build(MagicMock(spec=User)) == []


async def test_build_no_data_returns_empty_and_drops_empty_sections():
    svc, comms = _svc([])
    user = MagicMock(spec=User)
    user.timezone = None

    async def empty(_ctx):
        return {"key": "a", "title": "A", "items": []}

    async def none(_ctx):
        return None

    async def full(_ctx):
        return {"key": "b", "title": "B", "items": [{"text": "x", "link": "/y"}]}

    with (
        patch("app.services.recap_service.CommunityRepository", return_value=comms),
        patch("app.services.recap_service.SECTIONS", [empty, none]),
    ):
        assert await svc.build(user) == []
    with (
        patch("app.services.recap_service.CommunityRepository", return_value=comms),
        patch("app.services.recap_service.SECTIONS", [empty, full]),
    ):
        assert [s["key"] for s in await svc.build(user)] == ["b"]


def _ctx(features=None):
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    return recap_sections.RecapContext(user, _comm(features), MagicMock(), SUN, SUN.date(), "UTC")


async def test_on_this_day_section_only_uses_visible_posts_and_respects_flag():
    visible = {"id": "p1", "content": "Beach  day\nwith everyone"}
    with patch("app.services.recap_sections.MemoriesService") as ms:
        ms.return_value.on_this_day = AsyncMock(return_value={"items": [visible], "years_ago": [3]})
        sec = await recap_sections.on_this_day(_ctx())
        assert sec is not None
        assert sec["items"] == [
            {"text": "3 years ago: Beach day with everyone", "link": "/app/post/p1"}
        ]
        assert await recap_sections.on_this_day(_ctx({"on_this_day": False})) is None
        ms.return_value.on_this_day.assert_awaited_once()


async def test_capsules_section_only_recent_opened():
    def cap(days):
        c = MagicMock()
        c.id = uuid.uuid4()
        c.title = "T"
        c.author.display_name = "Ruth"
        c.opened_at = SUN - timedelta(days=days)
        return c

    with patch("app.services.recap_sections.TimeCapsuleService") as ts:
        ts.return_value.list_for_viewer = AsyncMock(return_value={"opened": [cap(2), cap(20)]})
        sec = await recap_sections.capsules_opened(_ctx())
    assert sec is not None and len(sec["items"]) == 1


async def test_daily_question_counts_answers():
    pid = uuid.uuid4()
    with patch("app.services.recap_sections.RecapRepository") as rr:
        rr.return_value.yesterday_daily = AsyncMock(return_value=(pid, "Fave food?", 1))
        sec = await recap_sections.daily_question(_ctx())
    assert sec is not None and sec["items"][0]["text"] == "Fave food? (1 answer)"


def test_prefs_patch_accepts_recap_cadence():
    from app.schemas.notification import NotificationPreferencesUpdate
    from app.services.notifications.api_helpers import build_prefs_update

    patch_ = NotificationPreferencesUpdate(recap_cadence="off")
    assert build_prefs_update(patch_, {}) == {"recap_cadence": "off"}


async def test_newsletter_link_only_for_monthly_readers_and_flag():
    ctx = _ctx()
    ctx.community.created_at = SUN - timedelta(days=400)
    with patch("app.services.recap_sections.RecapRepository") as rr:
        rr.return_value.cadence = AsyncMock(return_value="monthly")
        sec = await recap_sections.newsletter_link(ctx)
        assert sec is not None
        month = f"{(SUN.replace(day=1) - timedelta(days=1)):%Y-%m}"
        assert sec["items"][0]["link"] == f"/app/newsletter/{month}"
        assert await recap_sections.newsletter_link(_ctx({"newsletter": False})) is None
        rr.return_value.cadence = AsyncMock(return_value="weekly")
        assert await recap_sections.newsletter_link(ctx) is None
