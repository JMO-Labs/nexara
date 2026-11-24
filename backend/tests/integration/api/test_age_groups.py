"""
@file test_age_groups.py
@brief Integration tests for /api/v1/age-groups and /api/v1/admin/age-groups.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.core.deps_age import get_age_service
from app.repositories.age_repo import AgeRepository
from app.services.age_service import AgeService

CID = uuid.uuid4()
SUBJECT = uuid.uuid4()


@pytest.fixture
def env(test_app):
    repo = AsyncMock(spec=AgeRepository)
    audit = MagicMock(append=AsyncMock())
    state: dict = {}

    def client(role="admin"):
        me = SimpleNamespace(id=uuid.uuid4(), role=role, community_id=CID)
        test_app.dependency_overrides[get_current_user] = lambda: me
        svc = AgeService(repo, CID, me.id, audit, MagicMock(notify=AsyncMock()))
        test_app.dependency_overrides[get_age_service] = lambda: svc
        state["me"] = me
        return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")

    yield SimpleNamespace(client=client, repo=repo, audit=audit, state=state)
    test_app.dependency_overrides.clear()


def _row(subject=SUBJECT, status="pending"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        subject_id=subject,
        suggested_by=uuid.uuid4(),
        age_group="teen",
        note=None,
        status=status,
        decided_by=None,
        decided_at=None,
        created_at=datetime.now(UTC),
    )


async def test_suggest_self_400(env):
    async with env.client("member") as c:
        r = await c.post(
            "/api/v1/age-groups/suggestions",
            json={"subject_id": str(env.state["me"].id), "age_group": "teen"},
        )
    assert r.status_code == 400


async def test_member_can_suggest(env):
    env.repo.get_user.return_value = SimpleNamespace(id=SUBJECT)
    env.repo.pending_exists.return_value = False
    env.repo.list_admin_ids.return_value = []
    env.repo.create.return_value = _row()
    async with env.client("member") as c:
        r = await c.post(
            "/api/v1/age-groups/suggestions",
            json={"subject_id": str(SUBJECT), "age_group": "teen", "note": "13"},
        )
    assert r.status_code == 201


async def test_admin_approve_sets_group_and_audits(env):
    row = _row()
    user = SimpleNamespace(age_group=None)
    env.repo.get.return_value = row
    env.repo.get_user.return_value = user
    async with env.client("admin") as c:
        r = await c.post(f"/api/v1/admin/age-groups/suggestions/{row.id}/approve")
    assert r.status_code == 200
    env.repo.set_user_group.assert_awaited_with(user, "teen")
    assert env.audit.append.await_args.kwargs["action"] == "age_group.suggestion.approved"


async def test_admin_set_user_group_audits(env):
    env.repo.get_user.return_value = SimpleNamespace(age_group=None)
    async with env.client("admin") as c:
        r = await c.put(f"/api/v1/admin/users/{SUBJECT}/age-group", json={"age_group": "adult"})
    assert r.status_code == 200
    assert env.audit.append.await_args.kwargs["action"] == "age_group.set"


async def test_member_cannot_approve(env):
    async with env.client("member") as c:
        a = await c.post(f"/api/v1/admin/age-groups/suggestions/{uuid.uuid4()}/approve")
        b = await c.get("/api/v1/admin/age-groups/suggestions")
        d = await c.put("/api/v1/admin/age-groups/settings", json={"adult_requires_approval": True})
    assert (a.status_code, b.status_code, d.status_code) == (403, 403, 403)
