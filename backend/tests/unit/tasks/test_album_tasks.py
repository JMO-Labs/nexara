"""
@file test_album_tasks.py
@brief Unit tests for the "share your photos" album reminder (idempotent beat job).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.community import Community
from app.repositories.album_repo import AlbumRepository
from app.services.album_service import AlbumService
from app.tasks import album_tasks
from tests.unit.services.strict_notify import strict_notify

CID = uuid.uuid4()
NOW = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)


def _event(ended_hours_ago: float, reminded: bool = False) -> MagicMock:
    ev = MagicMock()
    ev.id = uuid.uuid4()
    ev.community_id = CID
    ev.title = "Picnic"
    ev.ends_at = NOW - timedelta(hours=ended_hours_ago)
    ev.album_reminded_at = NOW if reminded else None
    return ev


def _svc(rows, going, features=None):
    """Repo fake mirroring the SQL window + stamp filter so idempotency is observable."""
    repo = AsyncMock(spec=AlbumRepository)
    stamped: set[uuid.UUID] = set()

    async def due(now, lo, hi):
        return [
            (e, gid)
            for e, gid in rows
            if lo <= e.ends_at <= hi and e.id not in stamped and not e.album_reminded_at
        ]

    async def stamp(ids, now):
        stamped.update(ids)

    repo.due_for_reminder.side_effect = due
    repo.stamp_reminded.side_effect = stamp
    repo.going_user_ids.return_value = going
    comms = AsyncMock()
    comm = MagicMock(spec=Community)
    comm.features = features or {}
    comms.get.return_value = comm
    notif = strict_notify()
    return AlbumService(repo, comms, notif, CID), notif


async def test_fires_once_for_event_ended_20h_ago():
    gid, u1, u2 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    svc, notif = _svc([(_event(20), gid)], [u1, u2])
    assert await svc.remind_due(NOW) == 1
    assert notif.notify.await_count == 2
    uid, typ, payload = notif.notify.await_args_list[0].args[:3]
    assert typ == "album_reminder" and payload["gallery_id"] == str(gid)
    assert payload["title"] == "Picnic" and payload["link"].endswith(str(gid))


async def test_not_fired_for_event_ended_40h_ago():
    svc, notif = _svc([(_event(40), uuid.uuid4())], [uuid.uuid4()])
    assert await svc.remind_due(NOW) == 0
    notif.notify.assert_not_awaited()


async def test_not_fired_twice():
    svc, notif = _svc([(_event(20), uuid.uuid4())], [uuid.uuid4()])
    await svc.remind_due(NOW)
    await svc.remind_due(NOW)
    assert notif.notify.await_count == 1


async def test_only_going_rsvps_queried():
    svc, _ = _svc([(_event(20), uuid.uuid4())], [])
    await svc.remind_due(NOW)
    svc._repo.going_user_ids.assert_awaited_once()


async def test_feature_off_skips_but_stamps_nothing_sent():
    svc, notif = _svc([(_event(20), uuid.uuid4())], [uuid.uuid4()], {"event_albums": False})
    assert await svc.remind_due(NOW) == 0
    notif.notify.assert_not_awaited()


async def test_new_albums_section_uses_repo_and_flag():
    from app.services import recap_sections

    g = MagicMock()
    g.id, g.title = uuid.uuid4(), "Picnic"
    ctx = recap_sections.RecapContext(
        MagicMock(), MagicMock(spec=Community), MagicMock(), NOW, NOW.date(), "UTC"
    )
    ctx.community.features = {}
    ctx.community.id = CID
    with patch("app.services.recap_sections.AlbumRepository") as repo:
        repo.return_value.new_event_galleries = AsyncMock(return_value=[g])
        sec = await recap_sections.new_albums(ctx)
    assert sec is not None and sec["key"] == "new_albums"
    assert sec["items"][0]["link"] == f"/app/photos?gallery={g.id}"
    ctx.community.features = {"event_albums": False}
    assert await recap_sections.new_albums(ctx) is None


def test_runner_commits_and_beat_wired():
    from app.tasks.celery_app import celery_app

    session = AsyncMock()
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    with (
        patch.object(album_tasks, "async_session_factory", factory),
        patch.object(album_tasks, "AlbumService") as cls,
    ):
        cls.return_value.remind_due = AsyncMock(return_value=2)
        assert album_tasks.remind() == {"reminded": 2}
    session.commit.assert_awaited_once()
    assert any(v["task"] == "albums.remind" for v in celery_app.conf.beat_schedule.values())
