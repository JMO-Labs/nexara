"""
@file test_onboarding.py
@brief Integration tests for /api/v1/onboarding and /api/v1/admin/onboarding.
"""

from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.core.deps_onboarding import get_onboarding_service
from app.repositories.onboarding_repo import OnboardingRepository
from app.services.onboarding_service import OnboardingService

CID = uuid.uuid4()


def _user(**kw):
    base = dict(
        id=uuid.uuid4(),
        role="member",
        community_id=CID,
        display_name="Sso Sam",
        avatar_url="https://idp/x.png",
        email="sam@example.com",
        onboarding_step=0,
        onboarding_done_at=None,
        birthday=None,
        phone=None,
        contact_email=None,
        address=None,
        location=None,
        password_hash="x",
    )
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture
def env(test_app):
    repo = AsyncMock(spec=OnboardingRepository)
    repo.get_community.return_value = SimpleNamespace(onboarding_required=[])
    repo.has_relation.return_value = False
    audit = MagicMock(append=AsyncMock())
    state: dict = {}
    patches = [
        patch("app.services.onboarding_service.TwoFactorRepository"),
        patch("app.services.onboarding_service.factor_methods", AsyncMock(return_value=[])),
    ]
    mocks = [p.start() for p in patches]
    mocks[0].return_value.get_policy = AsyncMock(return_value="off")

    def client(role="member", **kw):
        me = _user(role=role, **kw)
        test_app.dependency_overrides[get_current_user] = lambda: me
        svc = OnboardingService(repo, CID, MagicMock(), me, audit)
        test_app.dependency_overrides[get_onboarding_service] = lambda: svc
        state["me"] = me
        return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")

    yield SimpleNamespace(client=client, repo=repo, audit=audit, state=state, policy=mocks[0])
    for p in patches:
        p.stop()
    test_app.dependency_overrides.clear()


async def test_state_prefills_sso_name(env):
    async with env.client() as c:
        r = await c.get("/api/v1/onboarding")
    body = r.json()
    assert r.status_code == 200
    assert body["prefill"]["display_name"] == "Sso Sam"
    assert body["done"] is False
    assert body["steps"][0] == "profile"


async def test_put_step_persists_and_resumes(env):
    async with env.client() as c:
        r = await c.put("/api/v1/onboarding", json={"step": 3})
    assert r.status_code == 200
    env.repo.set_step.assert_awaited_with(env.state["me"], 3)


async def test_required_birthday_blocks_complete(env):
    env.repo.get_community.return_value = SimpleNamespace(onboarding_required=["birthday"])
    async with env.client() as c:
        r = await c.post("/api/v1/onboarding/complete")
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "onboarding_incomplete"
    assert err["details"]["missing"] == ["birthday"]
    env.repo.mark_done.assert_not_awaited()


async def test_complete_when_requirements_met(env):
    env.repo.get_community.return_value = SimpleNamespace(onboarding_required=["birthday"])
    async with env.client(birthday=date(1990, 1, 1)) as c:
        r = await c.post("/api/v1/onboarding/complete")
    assert r.status_code == 200
    env.repo.mark_done.assert_awaited_once()


async def test_skippable_steps_do_not_block(env):
    async with env.client() as c:
        r = await c.post("/api/v1/onboarding/complete")
    assert r.status_code == 200


async def test_security_required_when_policy_covers(env):
    env.policy.return_value.get_policy = AsyncMock(return_value="everyone")
    async with env.client() as c:
        s = await c.get("/api/v1/onboarding")
        r = await c.post("/api/v1/onboarding/complete")
    assert "security" in s.json()["required"]
    assert r.status_code == 400
    assert r.json()["error"]["details"]["missing"] == ["security"]


async def test_admin_sets_required_and_audits(env):
    async with env.client("admin") as c:
        r = await c.put("/api/v1/admin/onboarding", json={"required": ["birthday", "profile"]})
    assert r.status_code == 200
    assert r.json()["required"] == ["profile", "birthday"]
    env.repo.set_required.assert_awaited_with(CID, ["profile", "birthday"])
    assert env.audit.append.await_args.kwargs["action"] == "onboarding.required_updated"


async def test_member_cannot_set_required(env):
    async with env.client("member") as c:
        r = await c.put("/api/v1/admin/onboarding", json={"required": ["birthday"]})
    assert r.status_code == 403


async def test_unknown_step_422(env):
    async with env.client("admin") as c:
        r = await c.put("/api/v1/admin/onboarding", json={"required": ["nope"]})
    assert r.status_code == 422
