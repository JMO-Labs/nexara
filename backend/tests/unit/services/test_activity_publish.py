"""@file test_activity_publish.py
@brief Tests for record_activity (record + feed_ping to audience).
"""

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.repositories.activity_repo import ActivityRepository
from app.services.activity_publish import record_activity
from app.services.realtime.events import EventType

KW = {
    "community_id": uuid.uuid4(),
    "actor_id": uuid.uuid4(),
    "verb": "post.created",
    "object_type": "post",
    "object_id": uuid.uuid4(),
    "subgroup_id": None,
    "visibility": "community",
}


def _repo():
    repo = AsyncMock(spec=ActivityRepository)
    ev = MagicMock()
    ev.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    repo.record.return_value = ev
    return repo, ev


class TestRecordActivity:
    async def test_records_then_pings_audience_only(self):
        repo, ev = _repo()
        bus = AsyncMock()
        aud = [KW["actor_id"], uuid.uuid4()]
        with (
            patch(
                "app.services.activity_publish.resolve_audience", AsyncMock(return_value=aud)
            ) as ra,
            patch("app.services.activity_publish.emit_to_audience", AsyncMock()) as em,
        ):
            out = await record_activity(repo, MagicMock(), bus, **KW)
        assert out is ev
        repo.record.assert_awaited_once_with(**KW)
        assert ra.call_args.kwargs == {
            "visibility": "community",
            "subgroup_id": None,
            "author_id": KW["actor_id"],
        }
        em.assert_awaited_once_with(
            bus, aud, EventType.FEED_PING, {"at": ev.created_at.isoformat()}
        )

    async def test_emit_failure_not_raised(self):
        repo, ev = _repo()
        with (
            patch("app.services.activity_publish.resolve_audience", AsyncMock(return_value=[])),
            patch(
                "app.services.activity_publish.emit_to_audience",
                AsyncMock(side_effect=RuntimeError("boom")),
            ),
        ):
            assert await record_activity(repo, MagicMock(), AsyncMock(), **KW) is ev

    async def test_no_event_no_ping(self):
        repo = AsyncMock(spec=ActivityRepository)
        repo.record.return_value = None
        with patch("app.services.activity_publish.emit_to_audience", AsyncMock()) as em:
            assert await record_activity(repo, MagicMock(), AsyncMock(), **KW) is None
        em.assert_not_awaited()


def test_no_direct_record_calls_in_services():
    root = Path(__file__).resolve().parents[3] / "app" / "services"
    bad = [
        str(p)
        for p in root.rglob("*.py")
        if p.name != "activity_publish.py" and re.search(r"activity_repo\.record\(", p.read_text())
    ]
    assert bad == []
