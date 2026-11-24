"""@file test_admin_apprise_service.py @brief AdminAppriseService unit tests."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.models.apprise_url import AppriseURL
from app.repositories.apprise_repo import AppriseRepository
from app.services.admin_apprise_service import AdminAppriseService

CID = uuid4()


def _svc() -> tuple[AdminAppriseService, AsyncMock]:
    repo = AsyncMock(spec=AppriseRepository)
    return AdminAppriseService(repo, CID), repo


async def test_delete_member_row_is_404() -> None:
    svc, repo = _svc()
    row = MagicMock(spec=AppriseURL)
    row.is_admin_target = False
    row.community_id = CID
    repo.get.return_value = row
    with pytest.raises(NotFoundError):
        await svc.delete(uuid4())
    repo.delete.assert_not_awaited()


async def test_create_returns_refetched_row() -> None:
    svc, repo = _svc()
    created, fetched = MagicMock(spec=AppriseURL), MagicMock(spec=AppriseURL)
    created.id = uuid4()
    fetched.apprise_url = "ntfy://ntfy.sh/topic"
    repo.create.return_value = created
    repo.get.return_value = fetched
    out = await svc.create("ntfy://ntfy.sh/topic", "x")
    assert out is fetched
    assert out.apprise_url.partition("://")[0] == "ntfy"
    repo.get.assert_awaited_once_with(created.id)


async def test_delete_admin_row_ok() -> None:
    svc, repo = _svc()
    row = MagicMock(spec=AppriseURL)
    row.is_admin_target = True
    row.community_id = CID
    repo.get.return_value = row
    await svc.delete(uuid4())
    repo.delete.assert_awaited_once()
