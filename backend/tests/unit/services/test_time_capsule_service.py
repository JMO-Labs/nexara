"""
@file test_time_capsule_service.py
@brief Unit tests for TimeCapsuleService (AsyncMock repos).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.models.community import Community
from app.models.time_capsule import TimeCapsule, TimeCapsuleRecipient
from app.repositories.community_repo import CommunityRepository
from app.repositories.time_capsule_repo import TimeCapsuleRepository
from app.schemas.time_capsule import CapsuleCreate, CapsuleOpen, CapsuleRecipient, CapsuleSealed
from app.services.time_capsule_service import TimeCapsuleService
from tests.unit.services.strict_notify import strict_notify

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
AUTHOR, MAYA = uuid.uuid4(), uuid.uuid4()


def _cap(opened: bool = False, author: uuid.UUID = AUTHOR) -> MagicMock:
    c = MagicMock(spec=TimeCapsule)
    c.id, c.community_id, c.author_id = uuid.uuid4(), CID, author
    c.title, c.body, c.media_ids = "For Maya", "secret words", [uuid.uuid4()]
    c.open_at = datetime.now(UTC) + timedelta(days=30)
    c.opened_at = datetime.now(UTC) if opened else None
    return c


@pytest.fixture
def svc():
    repo = AsyncMock(spec=TimeCapsuleRepository)
    comm = AsyncMock(spec=CommunityRepository)
    community = MagicMock(spec=Community)
    community.features = {}
    comm.get.return_value = community
    repo.author_names.return_value = {AUTHOR: "Ruth"}
    repo.visible_user_ids.side_effect = lambda ids, *_: set(ids)
    repo.recipients.return_value = []
    repo.own_media_count.return_value = 0
    notif = strict_notify()
    return TimeCapsuleService(repo, comm, notif, CID), repo, comm, community, notif


def _body(**kw) -> CapsuleCreate:
    d = {
        "title": "t",
        "body": "b",
        "open_at": datetime.now(UTC) + timedelta(days=10),
        "recipients": [CapsuleRecipient(kind="user", target_id=MAYA)],
    }
    d.update(kw)
    return CapsuleCreate(**d)


@pytest.mark.parametrize("delta", [timedelta(hours=2), timedelta(days=365 * 51)])
async def test_create_rejects_bad_open_at(svc, delta) -> None:
    service, *_ = svc
    with pytest.raises(AppError) as e:
        await service.create(AUTHOR, _body(open_at=datetime.now(UTC) + delta))
    assert e.value.status_code == 422


async def test_create_rejects_unaddressable_recipient(svc) -> None:
    service, repo, *_ = svc
    repo.visible_user_ids.side_effect = None
    repo.visible_user_ids.return_value = set()
    with pytest.raises(AppError) as e:
        await service.create(AUTHOR, _body())
    assert e.value.status_code == 422


async def test_create_rejects_foreign_media(svc) -> None:
    service, repo, *_ = svc
    repo.own_media_count.return_value = 0
    with pytest.raises(AppError):
        await service.create(AUTHOR, _body(media_ids=[uuid.uuid4()]))


async def test_create_ok_stores_recipients(svc) -> None:
    service, repo, *_ = svc
    repo.create.return_value = _cap()
    out = await service.create(AUTHOR, _body())
    assert isinstance(out, CapsuleOpen)
    assert repo.create.await_args.kwargs["recipients"] == [("user", MAYA)]


async def test_feature_off_is_404(svc) -> None:
    service, _, _, community, _ = svc
    community.features = {"time_capsules": False}
    with pytest.raises(AppError) as e:
        await service.get(uuid.uuid4(), MAYA)
    assert e.value.status_code == 404


async def test_recipient_sees_sealed_without_body(svc) -> None:
    service, repo, *_ = svc
    repo.get.return_value = _cap()
    repo.is_recipient.return_value = True
    out = await service.get(uuid.uuid4(), MAYA)
    assert isinstance(out, CapsuleSealed) and not isinstance(out, CapsuleOpen)
    assert "body" not in out.model_dump_json() and "media" not in out.model_dump()


async def test_author_sees_body_before_open(svc) -> None:
    service, repo, *_ = svc
    repo.get.return_value = _cap()
    out = await service.get(uuid.uuid4(), AUTHOR)
    assert isinstance(out, CapsuleOpen) and out.body == "secret words"


async def test_opened_shows_body_to_recipient(svc) -> None:
    service, repo, *_ = svc
    repo.get.return_value = _cap(opened=True)
    repo.is_recipient.return_value = True
    assert isinstance(await service.get(uuid.uuid4(), MAYA), CapsuleOpen)


async def test_non_recipient_404(svc) -> None:
    service, repo, *_ = svc
    repo.get.return_value = _cap()
    repo.is_recipient.return_value = False
    with pytest.raises(NotFoundError):
        await service.get(uuid.uuid4(), uuid.uuid4())


async def test_blocked_author_404(svc) -> None:
    service, repo, *_ = svc
    repo.get.return_value = _cap()
    repo.is_recipient.return_value = True
    repo.visible_user_ids.side_effect = None
    repo.visible_user_ids.return_value = set()
    with pytest.raises(NotFoundError):
        await service.get(uuid.uuid4(), MAYA)


async def test_delete_author_only(svc) -> None:
    service, repo, *_ = svc
    repo.get.return_value = _cap()
    with pytest.raises(AuthorizationError):
        await service.delete(uuid.uuid4(), MAYA)
    await service.delete(uuid.uuid4(), AUTHOR)
    repo.delete.assert_awaited_once()


async def test_list_groups_by_state(svc) -> None:
    service, repo, *_ = svc
    repo.list_for_viewer.return_value = [
        _cap(author=MAYA),
        _cap(opened=True, author=MAYA),
        _cap(),
    ]
    out = await service.list_for_viewer(AUTHOR)
    assert (len(out["sealed"]), len(out["opened"]), len(out["mine"])) == (1, 1, 1)
    assert all(not hasattr(s, "body") for s in out["sealed"])


async def test_open_due_notifies_each_recipient_once(svc) -> None:
    service, repo, _, _, notif = svc
    household_owner = uuid.uuid4()
    repo.claim_due.side_effect = [[_cap()], []]
    repo.resolve_user_ids.return_value = {MAYA, household_owner}
    now = datetime.now(UTC)
    assert await service.open_due(now) == 1
    assert await service.open_due(now) == 0
    assert sorted(c.args[0] for c in notif.notify.await_args_list) == sorted(
        [MAYA, household_owner]
    )
    assert notif.notify.await_args.args[1] == "capsule_opened"
    payload = notif.notify.await_args.args[2]
    assert "secret words" not in str(payload)
    assert {"capsule_id", "title", "author_name", "link"} <= payload.keys()


def test_recipient_model_importable() -> None:
    assert TimeCapsuleRecipient.__tablename__ == "time_capsule_recipients"
