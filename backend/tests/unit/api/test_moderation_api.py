"""
@file test_moderation_api.py
@brief Unit tests for moderation API routes (roles, routing, error envelope).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError


def _user(role: str) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    return u


@pytest.fixture
def as_role(test_app):
    from app.core.dependencies import get_current_user, get_db

    def _set(role: str) -> MagicMock:
        user = _user(role)

        async def _override():
            return user

        test_app.dependency_overrides[get_current_user] = _override
        return user

    async def _db():
        yield AsyncMock()

    test_app.dependency_overrides[get_db] = _db
    yield _set
    test_app.dependency_overrides.pop(get_current_user, None)
    test_app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def repo():
    with (
        patch("app.api.v1.moderation.ModerationRepository") as repo_cls,
        patch("app.api.v1.moderation.AuditRepository") as audit_cls,
    ):
        r = AsyncMock()
        repo_cls.return_value = r
        audit_cls.return_value = AsyncMock()
        yield r


async def _call(app, method: str, url: str, json: dict | None = None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        return await c.request(method, "/api/v1" + url, json=json)


def _report_body() -> dict:
    return {"target_type": "post", "target_id": str(uuid.uuid4()), "reason": "spam"}


@pytest.mark.parametrize(
    ("method", "url", "body"),
    [
        ("GET", "/admin/moderation/reports", None),
        ("POST", f"/admin/moderation/reports/{uuid.uuid4()}/action", {"action": "dismiss"}),
    ],
)
async def test_non_admin_gets_403(test_app, as_role, repo, method, url, body):
    as_role("member")
    resp = await _call(test_app, method, url, body)
    assert resp.status_code == 403
    assert "error" in resp.json()
    repo.get_report.assert_not_awaited()
    repo.list_reports.assert_not_awaited()


async def test_users_blocked_routes_to_list_blocked(test_app, as_role, repo):
    user = as_role("member")
    block = MagicMock()
    block.id, block.blocker_id, block.blocked_id = uuid.uuid4(), user.id, uuid.uuid4()
    block.created_at = datetime.now(UTC)
    repo.list_blocks = AsyncMock(return_value=[block])
    resp = await _call(test_app, "GET", "/users/blocked")
    assert resp.status_code == 200
    assert resp.json()[0]["blocked_id"] == str(block.blocked_id)
    repo.list_blocks.assert_awaited_once()


async def test_duplicate_report_409_envelope(test_app, as_role, repo):
    as_role("member")
    repo.content_exists = AsyncMock(return_value=True)
    repo.create_report = AsyncMock(side_effect=IntegrityError("x", {}, Exception()))
    resp = await _call(test_app, "POST", "/moderation/reports", _report_body())
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


async def test_report_unknown_target_404(test_app, as_role, repo):
    as_role("member")
    repo.content_exists = AsyncMock(return_value=False)
    resp = await _call(test_app, "POST", "/moderation/reports", _report_body())
    assert resp.status_code == 404
    assert "error" in resp.json()


async def test_invalid_reason_422(test_app, as_role, repo):
    as_role("member")
    body = {**_report_body(), "reason": "boring"}
    resp = await _call(test_app, "POST", "/moderation/reports", body)
    assert resp.status_code == 422
    assert "error" in resp.json()
    repo.create_report.assert_not_awaited()


async def test_invalid_action_422(test_app, as_role, repo):
    as_role("admin")
    url = f"/admin/moderation/reports/{uuid.uuid4()}/action"
    resp = await _call(test_app, "POST", url, {"action": "nuke"})
    assert resp.status_code == 422
    assert "error" in resp.json()
    repo.get_report.assert_not_awaited()


async def test_block_unknown_user_404(test_app, as_role, repo):
    as_role("member")
    repo.user_exists = AsyncMock(return_value=False)
    resp = await _call(test_app, "POST", f"/users/{uuid.uuid4()}/block")
    assert resp.status_code == 404
    repo.create_block.assert_not_awaited()


def _report_row(status: str = "pending", action: str | None = None) -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        reporter_id=uuid.uuid4(),
        target_type="post",
        target_id=uuid.uuid4(),
        reason="spam",
        description=None,
        status=status,
        reviewed_by=None,
        reviewed_at=now if action else None,
        action_taken=action,
        admin_notes=None,
        created_at=now,
    )


async def test_create_report_201(test_app, as_role, repo):
    as_role("member")
    row = _report_row()
    repo.content_exists = AsyncMock(return_value=True)
    repo.create_report = AsyncMock(return_value=row)
    resp = await _call(test_app, "POST", "/moderation/reports", _report_body())
    assert resp.status_code == 201
    assert resp.json()["id"] == str(row.id)
    assert resp.json()["status"] == "pending"


async def test_admin_lists_reports(test_app, as_role, repo):
    as_role("admin")
    row = _report_row()
    repo.list_reports = AsyncMock(return_value=([row], "next"))
    resp = await _call(test_app, "GET", "/admin/moderation/reports?status=pending&limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"][0]["id"] == str(row.id)
    assert body["next_cursor"] == "next"
    assert body["has_more"] is True
    assert repo.list_reports.call_args.kwargs["status_filter"] == "pending"


async def test_admin_dismisses_report(test_app, as_role, repo):
    admin = as_role("admin")
    row = _report_row()
    done = _report_row(status="dismissed", action="dismiss")
    done.reviewed_by = admin.id
    repo.get_report = AsyncMock(return_value=row)
    repo.mark_reviewed = AsyncMock(return_value=done)
    url = f"/admin/moderation/reports/{row.id}/action"
    resp = await _call(test_app, "POST", url, {"action": "dismiss"})
    assert resp.status_code == 200
    assert resp.json()["action_taken"] == "dismiss"
    assert resp.json()["reviewed_by"] == str(admin.id)


async def test_block_user_201(test_app, as_role, repo):
    user = as_role("member")
    target = uuid.uuid4()
    block = SimpleNamespace(
        id=uuid.uuid4(), blocker_id=user.id, blocked_id=target, created_at=datetime.now(UTC)
    )
    repo.user_exists = AsyncMock(return_value=True)
    repo.is_blocked = AsyncMock(return_value=False)
    repo.create_block = AsyncMock(return_value=block)
    resp = await _call(test_app, "POST", f"/users/{target}/block")
    assert resp.status_code == 201
    assert resp.json()["blocked_id"] == str(target)


async def test_unblock_user_204(test_app, as_role, repo):
    user = as_role("member")
    target = uuid.uuid4()
    repo.is_blocked = AsyncMock(return_value=True)
    resp = await _call(test_app, "DELETE", f"/users/{target}/block")
    assert resp.status_code == 204
    repo.remove_block.assert_awaited_once_with(user.id, target)
