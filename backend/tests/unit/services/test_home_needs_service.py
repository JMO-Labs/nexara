"""
@file test_home_needs_service.py
@brief Unit tests for HomeNeedsService.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from app.models.event import Event
from app.models.poll import Poll
from app.models.user import User
from app.repositories.home_needs_repo import HomeNeedsRepository
from app.repositories.subgroup_member_repo import SubgroupMemberRepository
from app.services.home_needs_service import HomeNeedsService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _build(sub_ids: dict[uuid.UUID, str] | None = None):
    repo = AsyncMock(spec=HomeNeedsRepository)
    repo.pending_rsvps.return_value = []
    repo.open_polls.return_value = []
    repo.unanswered_prompt.return_value = None
    repo.due_list_items.return_value = (0, None, None)
    members = AsyncMock(spec=SubgroupMemberRepository)
    members.list_my_roles.return_value = sub_ids or {}
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    return HomeNeedsService(repo, members, COMMUNITY_ID), repo, members, user


async def test_empty_results_give_empty_response():
    svc, _, _, user = _build()
    r = await svc.get(user)
    assert r.rsvps == [] and r.polls == [] and r.prompt is None and r.list_items is None


async def test_passes_subgroup_ids_from_my_roles():
    sid = uuid.uuid4()
    svc, repo, members, user = _build({sid: "member"})
    await svc.get(user)
    members.list_my_roles.assert_awaited_once_with(user.id)
    assert repo.pending_rsvps.call_args.args[2] == [sid]
    assert repo.open_polls.call_args.args[2] == [sid]
    assert repo.due_list_items.call_args.args[2] == [sid]


async def test_maps_rows():
    svc, repo, _, user = _build()
    ev = MagicMock(spec=Event)
    ev.id, ev.title, ev.starts_at = uuid.uuid4(), "Picnic", datetime(2026, 11, 20, tzinfo=UTC)
    poll = MagicMock(spec=Poll)
    poll.post_id, poll.question = uuid.uuid4(), "Pizza?"
    repo.pending_rsvps.return_value = [ev]
    repo.open_polls.return_value = [poll]
    pp, post, lid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    repo.unanswered_prompt.return_value = (pp, post, "Gratitude")
    repo.due_list_items.return_value = (3, lid, "Chores")
    r = await svc.get(user)
    assert r.rsvps[0].event_id == ev.id and r.rsvps[0].title == "Picnic"
    assert r.polls[0].post_id == poll.post_id and r.polls[0].question == "Pizza?"
    assert r.prompt is not None and r.prompt.prompt_post_id == pp and r.prompt.title == "Gratitude"
    assert r.list_items is not None and r.list_items.count == 3 and r.list_items.list_id == lid
