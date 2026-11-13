"""@file test_apprise_api.py
@brief Route-level tests for the Apprise URL endpoints (auth, shape, secrecy).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import notifications
from app.core.dependencies import get_current_user
from app.core.exceptions import AppError, NotFoundError
from app.models.apprise_url import AppriseURL
from app.services.apprise_service import AppriseService

BASE = "/api/v1/notifications/apprise"
SECRET = "slack://tokenA/tokenB/tokenC"


def _row() -> MagicMock:
    row = MagicMock(spec=AppriseURL)
    row.id = uuid.uuid4()
    row.label = "team"
    row.enabled = True
    row.failure_count = 0
    row.last_failure_at = None
    row.created_at = datetime.now(UTC)
    row.apprise_url = "gAAAA-ciphertext"
    return row


@pytest.fixture
def service() -> AsyncMock:
    return AsyncMock(spec=AppriseService)


@pytest.fixture
def client(test_app, service):
    user = MagicMock()
    user.id = uuid.uuid4()
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[notifications._apprise_service] = lambda: service
    yield AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")
    test_app.dependency_overrides.clear()


async def test_requires_auth(test_app) -> None:
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        assert (await c.get(BASE)).status_code in (401, 403)


async def test_list_excludes_url(client, service) -> None:
    service.list.return_value = [_row()]
    async with client as c:
        resp = await c.get(BASE)
    assert resp.status_code == 200
    assert "apprise_url" not in resp.json()[0]
    assert "ciphertext" not in resp.text


async def test_create_returns_no_url(client, service) -> None:
    service.create.return_value = _row()
    async with client as c:
        resp = await c.post(BASE, json={"apprise_url": SECRET, "label": "team"})
    assert resp.status_code == 201
    assert "apprise_url" not in resp.json()
    assert SECRET not in resp.text


async def test_create_invalid_url_400(client, service) -> None:
    service.create.side_effect = AppError(
        code="INVALID_APPRISE_URL", message="Invalid Apprise URL", status_code=400
    )
    async with client as c:
        resp = await c.post(BASE, json={"apprise_url": "nope://x"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_APPRISE_URL"


async def test_patch(client, service) -> None:
    row = _row()
    row.enabled = False
    service.update.return_value = row
    async with client as c:
        resp = await c.patch(f"{BASE}/{row.id}", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


async def test_patch_not_owned_404(client, service) -> None:
    service.update.side_effect = NotFoundError("x")
    async with client as c:
        resp = await c.patch(f"{BASE}/{uuid.uuid4()}", json={"label": "a"})
    assert resp.status_code == 404


async def test_delete(client, service) -> None:
    async with client as c:
        resp = await c.delete(f"{BASE}/{uuid.uuid4()}")
    assert resp.status_code == 200
    assert "message" in resp.json()


async def test_test_endpoint(client, service) -> None:
    service.test.return_value = (True, "Test notification sent")
    async with client as c:
        resp = await c.post(f"{BASE}/{uuid.uuid4()}/test")
    assert resp.json() == {"status": "sent", "message": "Test notification sent"}


async def test_test_endpoint_failure(client, service) -> None:
    service.test.return_value = (False, "Delivery failed")
    async with client as c:
        resp = await c.post(f"{BASE}/{uuid.uuid4()}/test")
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"
