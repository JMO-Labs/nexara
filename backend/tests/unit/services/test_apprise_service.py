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
    repo.allow_local.return_value = False
    return AppriseService(repo, CID), repo


def _row(user_id, community_id=CID) -> MagicMock:
    row = MagicMock(spec=AppriseURL)
    row.user_id = user_id
    row.community_id = community_id
    row.is_admin_target = False
    row.apprise_url = "discord://a/b"
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
    created = _row(uid)
    fetched = _row(uid)
    fetched.apprise_url = "ntfy://ntfy.sh/topic"
    repo.create.return_value = created
    repo.get.return_value = fetched
    out = await svc.create(uid, "discord://a/b", "x")
    repo.create.assert_awaited_once_with(CID, uid, "discord://a/b", "x")
    assert out is fetched
    assert out.apprise_url.partition("://")[0] == "ntfy"


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


async def test_list_includes_disabled() -> None:
    svc, repo = _svc()
    uid = uuid4()
    repo.list_for_user.return_value = [_row(uid)]
    assert await svc.list(uid) == repo.list_for_user.return_value
    repo.list_for_user.assert_awaited_once_with(uid, CID, enabled_only=False)


async def test_create_treats_apprise_exception_as_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(self, *a, **k):
        raise RuntimeError("bad")

    monkeypatch.setattr("apprise.Apprise.add", boom)
    svc, repo = _svc()
    with pytest.raises(AppError) as ei:
        await svc.create(uuid4(), "json://localhost", None)
    assert ei.value.code == "INVALID_APPRISE_URL"
    repo.create.assert_not_awaited()


async def test_test_sends_for_owned_row() -> None:
    svc, repo = _svc()
    uid, rid = uuid4(), uuid4()
    repo.get.return_value = _row(uid)
    repo.test_send.return_value = (True, "ok")
    assert await svc.test(uid, rid) == (True, "ok")
    repo.test_send.assert_awaited_once_with(rid, "Nexara test", "Test notification from Nexara")


async def test_member_create_private_blocked_422() -> None:
    svc, repo = _svc()
    with pytest.raises(AppError) as ei:
        await svc.create(uuid4(), "json://127.0.0.1/x", None)
    assert ei.value.code == "apprise_url_blocked" and ei.value.status_code == 422
    repo.create.assert_not_awaited()


async def test_member_create_private_ok_when_allow_local() -> None:
    svc, repo = _svc()
    repo.allow_local.return_value = True
    await svc.create(uuid4(), "json://127.0.0.1/x", None)
    repo.create.assert_awaited_once()


def _admin_row() -> MagicMock:
    row = _row(None)
    row.is_admin_target = True
    return row


async def test_member_test_admin_row_is_404() -> None:
    svc, repo = _svc()
    repo.get.return_value = _admin_row()
    with pytest.raises(NotFoundError):
        await svc.test(uuid4(), uuid4())
    repo.test_send.assert_not_awaited()


async def test_member_delete_admin_row_is_404() -> None:
    svc, repo = _svc()
    repo.get.return_value = _admin_row()
    with pytest.raises(NotFoundError):
        await svc.delete(uuid4(), uuid4())
    repo.delete.assert_not_awaited()
