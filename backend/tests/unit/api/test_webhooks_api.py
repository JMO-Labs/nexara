"""
@file test_webhooks_api.py
@brief Route tests for user and community webhook endpoints (service mocked).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user, get_webhook_service
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.services.webhook_service import WebhookService

NOW = datetime(2026, 1, 2, tzinfo=UTC)
CID = uuid.uuid4()
URL = "https://example.io/hook"
USER_BASE = "/api/v1/notifications/webhooks"


def _sub() -> MagicMock:
    s = MagicMock()
    s.id, s.url, s.type_keys, s.enabled = uuid.uuid4(), URL, ["a"], True
    s.failure_count, s.last_failure_at, s.created_at = 0, None, NOW
    return s


@pytest.fixture
def user() -> MagicMock:
    u = MagicMock(spec=User)
    u.id, u.community_id, u.role = uuid.uuid4(), CID, "admin"
    return u


@pytest.fixture
def service() -> AsyncMock:
    return AsyncMock(spec=WebhookService)


@pytest.fixture
async def client(
    test_app: FastAPI, user: MagicMock, service: AsyncMock
) -> AsyncIterator[AsyncClient]:
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[get_webhook_service] = lambda: service
    try:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
            yield c
    finally:
        test_app.dependency_overrides.clear()


async def test_user_list(client, service, user):
    service.list_for_user.return_value = [_sub()]
    r = await client.get(USER_BASE)
    assert r.status_code == 200 and r.json()[0]["url"] == URL
    service.list_for_user.assert_awaited_once_with(user.id)


async def test_user_create_returns_secret(client, service, user):
    service.create.return_value = (_sub(), "s3cret")
    r = await client.post(USER_BASE, json={"url": URL, "type_keys": ["a"]})
    assert r.status_code == 201 and r.json()["secret"] == "s3cret"
    service.create.assert_awaited_once_with(user.id, URL, ["a"])


async def test_user_update(client, service, user):
    service.update.return_value = _sub()
    wid = uuid.uuid4()
    r = await client.patch(f"{USER_BASE}/{wid}", json={"enabled": False})
    assert r.status_code == 200
    service.update.assert_awaited_once_with(user.id, wid, url=None, type_keys=None, enabled=False)


async def test_user_delete(client, service, user):
    wid = uuid.uuid4()
    r = await client.delete(f"{USER_BASE}/{wid}")
    assert r.status_code == 200
    service.delete.assert_awaited_once_with(user.id, wid)


async def test_user_delete_not_found(client, service):
    service.delete.side_effect = NotFoundError("nope")
    assert (await client.delete(f"{USER_BASE}/{uuid.uuid4()}")).status_code == 404


def _cbase(cid: uuid.UUID = CID) -> str:
    return f"/api/v1/communities/{cid}/webhooks"


async def test_community_foreign_community_forbidden(client, service):
    r = await client.get(_cbase(uuid.uuid4()))
    assert r.status_code == 403
    service.list_for_community.assert_not_awaited()


async def test_community_non_admin_forbidden(client, service, user):
    user.role = "member"
    assert (await client.get(_cbase())).status_code == 403


async def test_community_list(client, service):
    service.list_for_community.return_value = [_sub()]
    r = await client.get(_cbase())
    assert r.status_code == 200 and len(r.json()) == 1


async def test_community_create(client, service):
    service.create.return_value = (_sub(), "s3cret")
    r = await client.post(_cbase(), json={"url": URL})
    assert r.status_code == 201 and r.json()["secret"] == "s3cret"
    service.create.assert_awaited_once_with(None, URL, [])


async def test_community_update(client, service):
    service.update.return_value = _sub()
    wid = uuid.uuid4()
    r = await client.patch(f"{_cbase()}/{wid}", json={"url": URL, "enabled": True})
    assert r.status_code == 200
    service.update.assert_awaited_once_with(None, wid, url=URL, type_keys=None, enabled=True)


async def test_community_delete(client, service):
    wid = uuid.uuid4()
    r = await client.delete(f"{_cbase()}/{wid}")
    assert r.status_code == 200
    service.delete.assert_awaited_once_with(None, wid)


async def test_get_webhook_service_scoped_to_configured_community():
    from app.core.config import Settings
    from app.core.dependencies import get_webhook_repo

    session = MagicMock()
    repo = await get_webhook_repo(session)
    svc = await get_webhook_service(repo, Settings(COMMUNITY_ID=str(CID)))
    assert svc._community_id == CID and svc._repo is repo
