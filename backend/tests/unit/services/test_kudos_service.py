"""
@file test_kudos_service.py
@brief Unit tests for KudosService.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.models.post import Post
from app.models.user import User
from app.repositories.kudos_repo import KudosRepository
from app.repositories.subgroup_repo import SubgroupRepository
from app.repositories.user_repo import UserRepository
from app.schemas.kudos import KudosCreate
from app.services.kudos_service import KudosService
from app.services.notification_service import PREF_MAP, NotificationService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
AUTHOR_ID = uuid.uuid4()
RECIPIENT_ID = uuid.uuid4()


@pytest.fixture
def repos():
    kudos = AsyncMock(spec=KudosRepository)
    users = AsyncMock(spec=UserRepository)
    subs = AsyncMock(spec=SubgroupRepository)
    notif = AsyncMock(spec=NotificationService)
    recipient = MagicMock(spec=User)
    recipient.id = RECIPIENT_ID
    recipient.username = "bob"
    recipient.display_name = "Bob"
    recipient.avatar_url = None
    users.get_by_id.return_value = recipient
    subs.is_member.return_value = True
    post = MagicMock(spec=Post)
    post.id = uuid.uuid4()
    post.author_id = AUTHOR_ID
    post.recipient_id = RECIPIENT_ID
    post.content = "thanks"
    post.subgroup_id = None
    post.created_at = datetime.now(UTC)
    kudos.create_kudos.return_value = post
    kudos.get_by_id.return_value = post
    return kudos, users, subs, notif, post


@pytest.fixture
def service(repos):
    kudos, users, subs, notif, _ = repos
    return KudosService(kudos, users, subs, notif, COMMUNITY_ID)


def _author():
    u = MagicMock(spec=User)
    u.id = AUTHOR_ID
    return u


async def test_self_kudos_rejected(service):
    with pytest.raises(AppError) as exc:
        await service.create(_author(), KudosCreate(recipient_id=AUTHOR_ID))
    assert exc.value.status_code == 400


async def test_create_notifies_recipient(service, repos):
    _, _, _, notif, post = repos
    await service.create(_author(), KudosCreate(recipient_id=RECIPIENT_ID, message="thanks"))
    args = notif.notify.await_args
    assert args.args[0] == RECIPIENT_ID
    assert args.args[1] == "kudos_received"
    assert str(post.id) in args.args[2]["link"]


async def test_unknown_recipient_404(service, repos):
    repos[1].get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        await service.create(_author(), KudosCreate(recipient_id=RECIPIENT_ID))


async def test_subgroup_requires_membership(service, repos):
    repos[2].is_member.return_value = False
    with pytest.raises(AuthorizationError):
        await service.create(
            _author(), KudosCreate(recipient_id=RECIPIENT_ID, subgroup_id=uuid.uuid4())
        )


async def test_list_recent_and_received(service, repos):
    kudos = repos[0]
    kudos.list_kudos.return_value = ([], None)
    await service.list_recent(AUTHOR_ID)
    await service.list_received(RECIPIENT_ID, AUTHOR_ID)
    assert kudos.list_kudos.await_count == 2
    assert kudos.list_kudos.await_args.kwargs["recipient_id"] == RECIPIENT_ID


async def test_author_can_delete(service, repos):
    await service.delete(repos[4].id, _author())
    repos[0].soft_delete.assert_awaited_once()


async def test_non_author_delete_403(service, repos):
    other = _author()
    other.id = uuid.uuid4()
    with pytest.raises(AuthorizationError):
        await service.delete(repos[4].id, other)


async def test_missing_kudos_404(service, repos):
    repos[0].get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        await service.delete(uuid.uuid4(), _author())


def test_pref_map_has_kudos():
    assert "kudos_received" in PREF_MAP


async def test_subgroup_requires_recipient_membership(service, repos):
    repos[2].is_member.side_effect = [True, False]  # author yes, recipient no
    with pytest.raises(AuthorizationError):
        await service.create(
            _author(), KudosCreate(recipient_id=RECIPIENT_ID, subgroup_id=uuid.uuid4())
        )
