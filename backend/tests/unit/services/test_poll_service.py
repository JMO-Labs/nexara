"""
@file test_poll_service.py
@brief Unit tests for PollService.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError
from app.models.poll import Poll, PollOption, PollVote
from app.repositories.poll_repo import PollRepository
from app.services.poll_service import PollService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()
POLL_ID = uuid.uuid4()
OPTION_A = uuid.uuid4()
OPTION_B = uuid.uuid4()


@pytest.fixture
def poll_repo():
    return AsyncMock(spec=PollRepository)


@pytest.fixture
def event_bus():
    return AsyncMock()


@pytest.fixture
def service(poll_repo, event_bus):
    return PollService(
        poll_repo=poll_repo,
        community_id=COMMUNITY_ID,
        event_bus=event_bus,
    )


def _make_poll(poll_type="single", expires_at=None, closed=False):
    poll = MagicMock(spec=Poll)
    poll.id = POLL_ID
    poll.poll_type = poll_type
    poll.closed = closed
    poll.expires_at = expires_at
    poll.is_anonymous = False
    poll.result_visibility = "after_vote"
    poll.question = "Test?"
    poll.post_id = uuid.uuid4()
    poll.created_by = USER_ID
    poll.created_at = datetime.now(UTC)
    return poll


class TestCastVote:
    @pytest.mark.asyncio
    async def test_single_choice_rejects_multiple_options(self, service, poll_repo):
        poll = _make_poll(poll_type="single")
        poll_repo.get_by_id.return_value = poll

        with pytest.raises(AppError, match="single|one"):
            await service.cast_vote(POLL_ID, USER_ID, [OPTION_A, OPTION_B])

    @pytest.mark.asyncio
    async def test_vote_on_expired_poll_rejected(self, service, poll_repo):
        poll = _make_poll(expires_at=datetime.now(UTC) - timedelta(hours=1))
        poll_repo.get_by_id.return_value = poll

        with pytest.raises(AppError, match="expired|closed"):
            await service.cast_vote(POLL_ID, USER_ID, [OPTION_A])

    @pytest.mark.asyncio
    async def test_vote_on_closed_poll_rejected(self, service, poll_repo):
        poll = _make_poll(closed=True)
        poll_repo.get_by_id.return_value = poll

        with pytest.raises(AppError, match="expired|closed"):
            await service.cast_vote(POLL_ID, USER_ID, [OPTION_A])

    @pytest.mark.asyncio
    async def test_successful_vote_emits_sse(self, service, poll_repo, event_bus):
        poll = _make_poll(poll_type="single")
        opt = MagicMock(spec=PollOption)
        opt.id = OPTION_A
        opt.label = "Option A"
        opt.image_media_id = None
        opt.position = 0
        poll_repo.get_by_id.return_value = poll
        poll_repo.get_options.return_value = [opt]
        poll_repo.has_user_voted.return_value = False
        poll_repo.cast_vote.return_value = MagicMock(spec=PollVote)
        poll_repo.get_vote_counts.return_value = {OPTION_A: 1}
        poll_repo.get_user_votes.return_value = [OPTION_A]

        await service.cast_vote(POLL_ID, USER_ID, [OPTION_A])

        event_bus.emit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_option_rejected(self, service, poll_repo):
        poll = _make_poll(poll_type="single")
        poll_repo.get_by_id.return_value = poll
        poll_repo.get_options.return_value = [MagicMock(id=OPTION_A)]

        fake_option = uuid.uuid4()
        with pytest.raises(AppError, match="invalid|option"):
            await service.cast_vote(POLL_ID, USER_ID, [fake_option])


class TestCreatePoll:
    @pytest.mark.asyncio
    async def test_create_poll_with_valid_options(self, service, poll_repo):
        from app.schemas.poll import PollCreate, PollOptionCreate

        data = PollCreate(
            question="Favorite color?",
            poll_type="single",
            options=[
                PollOptionCreate(label="Red"),
                PollOptionCreate(label="Blue"),
            ],
        )
        post_id = uuid.uuid4()
        new_poll = MagicMock(spec=Poll)
        new_poll.id = POLL_ID
        new_poll.post_id = post_id
        new_poll.poll_type = "single"
        new_poll.question = "Favorite color?"
        new_poll.is_anonymous = False
        new_poll.result_visibility = "after_vote"
        new_poll.expires_at = None
        new_poll.closed = False
        new_poll.created_at = datetime.now(UTC)
        poll_repo.create.return_value = new_poll
        poll_repo.get_options.return_value = []
        poll_repo.get_vote_counts.return_value = {}

        await service.create_poll(USER_ID, data, post_id)

        poll_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_max_10_options_enforced(self, service, poll_repo):
        from app.schemas.poll import PollCreate, PollOptionCreate

        with pytest.raises(Exception):
            PollCreate(
                question="Too many?",
                poll_type="single",
                options=[PollOptionCreate(label=f"Opt {i}") for i in range(11)],
            )
