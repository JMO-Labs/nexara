"""@file test_apprise_service.py
@brief AppriseService: URL validation and ownership checks.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import AppError, NotFoundError
from app.models.apprise_url import AppriseURL
from app.repositories.apprise_repo import AppriseRepository
from app.services.apprise_service import AppriseService

CID = uuid4()


def _svc() -> tuple[AppriseService, AsyncMock]:
    repo = AsyncMock(spec=AppriseRepository)
    return AppriseService(repo, CID), repo


def _row(user_id, community_id=CID) -> MagicMock:
    row = MagicMock(spec=AppriseURL)
    row.user_id = user_id
    row.community_id = community_id
    return row


async def test_create_rejects_invalid_url() -> None:
    svc, repo = _svc()
    with pytest.raises(AppError) as ei:
        await svc.create(uuid4(), "not-a-url", None)
    assert ei.value.code == "INVALID_APPRISE_URL"
    assert ei.value.status_code == 400
    repo.create.assert_not_awaited()


async def test_create_stores_valid_url() -> None:
    svc, repo = _svc()
    uid = uuid4()
    await svc.create(uid, "json://localhost", "x")
    repo.create.assert_awaited_once_with(CID, uid, "json://localhost", "x")


async def test_other_users_row_is_404() -> None:
    svc, repo = _svc()
    repo.get.return_value = _row(uuid4())
    with pytest.raises(NotFoundError):
        await svc.delete(uuid4(), uuid4())
    repo.delete.assert_not_awaited()


async def test_update_applies_changes() -> None:
    svc, repo = _svc()
    uid = uuid4()
    repo.get.return_value = _row(uid)
    await svc.update(uid, uuid4(), "new", False)
    repo.set_enabled.assert_awaited_once()
    repo.set_label.assert_awaited_once()


async def test_test_checks_ownership_then_sends() -> None:
    svc, repo = _svc()
    uid = uuid4()
    repo.get.return_value = _row(uid)
    repo.test_send.return_value = (True, "ok")
    assert await svc.test(uid, uuid4()) == (True, "ok")
