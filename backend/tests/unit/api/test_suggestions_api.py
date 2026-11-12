"""
@file test_suggestions_api.py
@brief Unit tests for admin AI suggestion endpoints (service mocked via DI).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import ConflictError, NotFoundError

BASE = "/api/v1/admin/suggestions"
SID = uuid.uuid4()
ENDPOINTS = [
    ("GET", BASE),
    ("POST", f"{BASE}/generate"),
    ("POST", f"{BASE}/{SID}/approve"),
    ("POST", f"{BASE}/{SID}/reject"),
]
SHAPE = {
    "id",
    "type",
    "content",
    "suggested_by",
    "approved_at",
    "approved_by",
    "rejected_at",
    "created_at",
}


def _suggestion(**kw: object) -> MagicMock:
    s = MagicMock()
    s.id = SID
    s.type = "prompt"
    s.content = {"text": "What made you smile today?"}
    s.suggested_by = "ai"
    s.approved_at = None
    s.approved_by = None
    s.rejected_at = None
    s.created_at = datetime.now(UTC)
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def _as(test_app, role: str) -> MagicMock:
    from app.core.dependencies import get_current_user

    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = role

    async def _override():
        return user

    test_app.dependency_overrides[get_current_user] = _override
    return user


@pytest.fixture
def svc(test_app):
    from app.core.dependencies import get_suggestion_service

    service = AsyncMock()
    test_app.dependency_overrides[get_suggestion_service] = lambda: service
    yield service
    test_app.dependency_overrides.clear()


async def _call(test_app, method: str, url: str):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
        return await c.request(method, url)


@pytest.mark.parametrize(("method", "url"), ENDPOINTS)
async def test_non_admin_forbidden(test_app, svc, method, url):
    _as(test_app, "member")
    resp = await _call(test_app, method, url)
    assert resp.status_code == 403
    assert not svc.method_calls


async def test_list_returns_shape_and_passes_filters(test_app, svc):
    _as(test_app, "admin")
    svc.list_pending.return_value = [_suggestion()]
    resp = await _call(test_app, "GET", f"{BASE}?type=prompt&limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body[0]) == SHAPE
    assert body[0]["content"] == {"text": "What made you smile today?"}
    args = svc.list_pending.await_args.args
    assert args[1:] == ("prompt", 5, 0)


@pytest.mark.parametrize(
    "url", [f"{BASE}?type=bogus", f"{BASE}/generate?type=bogus", f"{BASE}?limit=0"]
)
async def test_invalid_input_422(test_app, svc, url):
    _as(test_app, "admin")
    method = "POST" if "generate" in url else "GET"
    assert (await _call(test_app, method, url)).status_code == 422


async def test_generate_poll_requires_topic(test_app, svc):
    _as(test_app, "admin")
    resp = await _call(test_app, "POST", f"{BASE}/generate?type=poll")
    assert resp.status_code == 422
    svc.generate_poll_suggestions.assert_not_awaited()


async def test_generate_prompt_counts(test_app, svc):
    _as(test_app, "admin")
    svc.generate_prompt_suggestions.return_value = ["a", "b"]
    resp = await _call(test_app, "POST", f"{BASE}/generate?type=prompt")
    assert resp.status_code == 200
    assert resp.json() == {"created": 2}


async def test_generate_poll_with_topic(test_app, svc):
    _as(test_app, "admin")
    svc.generate_poll_suggestions.return_value = ("Q?", ["a", "b", "c", "d"])
    resp = await _call(test_app, "POST", f"{BASE}/generate?type=poll&topic=food")
    assert resp.json() == {"created": 1}
    assert svc.generate_poll_suggestions.await_args.args[1] == "food"


async def test_approve_returns_shape(test_app, svc):
    user = _as(test_app, "admin")
    now = datetime.now(UTC)
    svc.approve.return_value = _suggestion(approved_at=now, approved_by=user.id)
    resp = await _call(test_app, "POST", f"{BASE}/{SID}/approve")
    assert resp.status_code == 200
    assert set(resp.json()) == SHAPE
    assert resp.json()["approved_by"] == str(user.id)
    assert svc.approve.await_args.args[:2] == (SID, user.id)


async def test_reject_returns_shape(test_app, svc):
    _as(test_app, "admin")
    svc.reject.return_value = _suggestion(rejected_at=datetime.now(UTC))
    resp = await _call(test_app, "POST", f"{BASE}/{SID}/reject")
    assert resp.status_code == 200
    assert set(resp.json()) == SHAPE
    assert resp.json()["rejected_at"] is not None


async def test_approve_twice_conflict(test_app, svc):
    _as(test_app, "admin")
    svc.approve.side_effect = [_suggestion(), ConflictError("Suggestion already reviewed")]
    assert (await _call(test_app, "POST", f"{BASE}/{SID}/approve")).status_code == 200
    resp = await _call(test_app, "POST", f"{BASE}/{SID}/approve")
    assert resp.status_code == 409
    assert "error" in resp.json()


@pytest.mark.parametrize("action", ["approve", "reject"])
async def test_unknown_id_404(test_app, svc, action):
    _as(test_app, "admin")
    getattr(svc, action).side_effect = NotFoundError("Suggestion not found")
    resp = await _call(test_app, "POST", f"{BASE}/{uuid.uuid4()}/{action}")
    assert resp.status_code == 404
