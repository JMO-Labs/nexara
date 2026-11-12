"""
@file test_kudos_api.py
@brief Unit tests for the kudos API routes and service wiring.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import kudos as kudos_module
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.kudos_service import KudosService

RECIPIENT_ID = uuid.uuid4()
EMPTY_LIST = {"kudos": [], "pagination": {"cursor": None, "has_more": False}}


@pytest.fixture
def user() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    return u


@pytest.fixture
def svc() -> AsyncMock:
    return AsyncMock(spec=KudosService)


@pytest.fixture
async def client(test_app, user, svc):
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[kudos_module._build_service] = lambda: svc
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        yield c
    test_app.dependency_overrides.clear()


async def test_create_kudos_returns_201(client, svc, user) -> None:
    svc.create.return_value = {
        "id": str(uuid.uuid4()),
        "recipient_id": str(RECIPIENT_ID),
        "message": "thanks",
        "author_id": str(user.id),
        "subgroup_id": None,
        "created_at": datetime.now(UTC).isoformat(),
        "recipient": None,
    }
    resp = await client.post(
        "/api/v1/kudos", json={"recipient_id": str(RECIPIENT_ID), "message": "thanks"}
    )
    assert resp.status_code == 201
    svc.create.assert_awaited_once()


async def test_list_kudos_passes_cursor_and_limit(client, svc, user) -> None:
    svc.list_recent.return_value = EMPTY_LIST
    resp = await client.get("/api/v1/kudos?limit=5&cursor=2026-01-01T00:00:00")
    assert resp.status_code == 200
    svc.list_recent.assert_awaited_once_with(user.id, "2026-01-01T00:00:00", 5)


async def test_list_received_passes_target_user(client, svc, user) -> None:
    svc.list_received.return_value = EMPTY_LIST
    resp = await client.get(f"/api/v1/kudos/user/{RECIPIENT_ID}")
    assert resp.status_code == 200
    svc.list_received.assert_awaited_once_with(RECIPIENT_ID, user.id, None, 20)


async def test_delete_kudos_returns_204(client, svc, user) -> None:
    kid = uuid.uuid4()
    resp = await client.delete(f"/api/v1/kudos/{kid}")
    assert resp.status_code == 204
    svc.delete.assert_awaited_once_with(kid, user)


def test_build_service_wires_dependencies() -> None:
    settings = MagicMock()
    settings.COMMUNITY_ID = "00000000-0000-0000-0000-000000000001"
    service = kudos_module._build_service(db=MagicMock(), settings=settings)
    assert isinstance(service, KudosService)
    assert service._community_id == uuid.UUID(settings.COMMUNITY_ID)
