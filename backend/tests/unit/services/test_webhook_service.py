"""
@file test_webhook_service.py
@brief Unit tests for WebhookService (ownership, secret handling).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import NotFoundError
from app.models.webhook import WebhookSubscription
from app.repositories.webhook_repo import WebhookRepository
from app.services.webhook_service import WebhookService

CID, UID = uuid.uuid4(), uuid.uuid4()


def _sub(user_id, community_id=CID):
    s = MagicMock(spec=WebhookSubscription)
    s.user_id, s.community_id = user_id, community_id
    return s


@pytest.fixture
def repo():
    return AsyncMock(spec=WebhookRepository)


async def test_create_generates_secret(repo):
    repo.create.side_effect = lambda *a, **k: _sub(UID)
    svc = WebhookService(repo, CID)
    _, secret = await svc.create(UID, "https://x.io", ["a"])
    assert len(secret) >= 32
    assert repo.create.await_args.args[3] == secret


async def test_update_other_users_sub_not_found(repo):
    repo.get.return_value = _sub(uuid.uuid4())
    with pytest.raises(NotFoundError):
        await WebhookService(repo, CID).update(UID, uuid.uuid4(), url="https://x.io")
    repo.update.assert_not_awaited()


async def test_delete_community_sub_via_user_scope_not_found(repo):
    repo.get.return_value = _sub(None)
    with pytest.raises(NotFoundError):
        await WebhookService(repo, CID).delete(UID, uuid.uuid4())
    repo.delete.assert_not_awaited()


async def test_delete_community_scope_requires_null_user(repo):
    repo.get.return_value = _sub(UID)
    with pytest.raises(NotFoundError):
        await WebhookService(repo, CID).delete(None, uuid.uuid4())


async def test_delete_wrong_community_not_found(repo):
    repo.get.return_value = _sub(UID, uuid.uuid4())
    with pytest.raises(NotFoundError):
        await WebhookService(repo, CID).delete(UID, uuid.uuid4())


async def test_delete_ok(repo):
    repo.get.return_value = _sub(UID)
    await WebhookService(repo, CID).delete(UID, uuid.uuid4())
    repo.delete.assert_awaited_once()
