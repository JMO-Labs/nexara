"""
@file test_nudge_service.py
@brief Unit tests for NudgeService (user-initiated and gentle nudges).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, AuthorizationError, NotFoundError, RateLimitError
from app.models.nudge import Nudge
from app.models.user import User
from app.repositories.nudge_repo import NudgeRepository
from app.repositories.user_repo import UserRepository
from app.services.notification_service import PREF_MAP
from app.services.nudge_service import NudgeService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SENDER = uuid.uuid4()
TARGET = uuid.uuid4()


def _nudge() -> MagicMock:
    n = MagicMock(spec=Nudge)
    n.id = uuid.uuid4()
    n.sender_id = SENDER
    n.target_id = TARGET
    n.nudge_type = "user_initiated"
    n.created_at = datetime.now(UTC)
    return n


@pytest.fixture
def deps():
    repo = AsyncMock(spec=NudgeRepository)
    users = AsyncMock(spec=UserRepository)
    notify = AsyncMock()
    target = MagicMock(spec=User)
    target.id = TARGET
    users.get_by_id.return_value = target
    repo.is_blocked.return_value = False
    repo.has_recent_user_nudge.return_value = False
    repo.create_nudge.return_value = _nudge()
    return repo, users, notify


@pytest.fixture
def service(deps):
    return NudgeService(deps[0], deps[1], deps[2], COMMUNITY_ID)


def test_pref_map_has_nudge_types():
    assert "nudge_received" in PREF_MAP
    assert "gentle_nudge" in PREF_MAP


async def test_send_creates_and_notifies(service, deps):
    sender = MagicMock(spec=User)
    sender.id = SENDER
    sender.display_name = "Ann"
    out = await service.send(sender, TARGET)
    deps[0].create_nudge.assert_awaited_once()
    args = deps[2].notify.await_args.args
    assert args[0] == TARGET
    assert args[1] == "nudge_received"
    assert args[2]["message"] == "Ann nudged you!"
    assert out["target_id"] == TARGET


async def test_self_nudge_rejected_400(service):
    sender = MagicMock(spec=User)
    sender.id = SENDER
    with pytest.raises(AppError) as ei:
        await service.send(sender, SENDER)
    assert ei.value.status_code == 400


async def test_rate_limited_429(service, deps):
    deps[0].has_recent_user_nudge.return_value = True
    sender = MagicMock(spec=User)
    sender.id = SENDER
    sender.display_name = "Ann"
    with pytest.raises(RateLimitError):
        await service.send(sender, TARGET)
    deps[0].create_nudge.assert_not_awaited()


async def test_blocked_by_target_rejected(service, deps):
    deps[0].is_blocked.return_value = True
    sender = MagicMock(spec=User)
    sender.id = SENDER
    sender.display_name = "Ann"
    with pytest.raises(AuthorizationError):
        await service.send(sender, TARGET)
    deps[0].create_nudge.assert_not_awaited()


async def test_unknown_target_404(service, deps):
    deps[1].get_by_id.return_value = None
    sender = MagicMock(spec=User)
    sender.id = SENDER
    with pytest.raises(NotFoundError):
        await service.send(sender, TARGET)


async def test_gentle_nudges_notify_each_candidate(service, deps):
    a, b = uuid.uuid4(), uuid.uuid4()
    deps[0].find_gentle_candidates.return_value = [a, b]
    count = await service.send_gentle_nudges(COMMUNITY_ID)
    assert count == 2
    assert deps[0].create_nudge.await_count == 2
    types = {c.args[1] for c in deps[2].notify.await_args_list}
    assert types == {"gentle_nudge"}
    assert deps[2].notify.await_args_list[0].args[2]["message"] == (
        "We miss you! Come check what's new."
    )


async def test_gentle_nudges_none(service, deps):
    deps[0].find_gentle_candidates.return_value = []
    assert await service.send_gentle_nudges(COMMUNITY_ID) == 0
    deps[2].notify.assert_not_awaited()
