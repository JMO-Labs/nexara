"""
@file test_onboarding.py
@brief Integration tests for /api/v1/onboarding and /api/v1/admin/onboarding.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
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
        two_factor_required_since=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture
def env(test_app):
    repo = AsyncMock(spec=OnboardingRepository)
    repo.get_community.return_value = SimpleNamespace(onboarding_required=[], features={})
    repo.has_family.return_value = False
    audit = MagicMock(append=AsyncMock())
    state: dict = {}
    two_factor = AsyncMock()
    two_factor.get_policy.return_value = "off"
    patches = [
        patch("app.services.onboarding_service.factor_methods", AsyncMock(return_value=[])),
    ]
    for p in patches:
        p.start()

    def client(role="member", **kw):
        me = _user(role=role, **kw)
        test_app.dependency_overrides[get_current_user] = lambda: me
        svc = OnboardingService(repo, CID, MagicMock(), me, audit, two_factor_repo=two_factor)
        test_app.dependency_overrides[get_onboarding_service] = lambda: svc
        state["me"] = me
        return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")

    yield SimpleNamespace(client=client, repo=repo, audit=audit, state=state, policy=two_factor)
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
    env.repo.get_community.return_value = SimpleNamespace(
        onboarding_required=["birthday"], features={}
    )
    async with env.client() as c:
        r = await c.post("/api/v1/onboarding/complete")
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "onboarding_incomplete"
    assert err["details"]["missing"] == ["birthday"]
    env.repo.mark_done.assert_not_awaited()


async def test_complete_when_requirements_met(env):
    env.repo.get_community.return_value = SimpleNamespace(
        onboarding_required=["birthday"], features={}
    )
    async with env.client(birthday=date(1990, 1, 1)) as c:
        r = await c.post("/api/v1/onboarding/complete")
    assert r.status_code == 200
    env.repo.mark_done.assert_awaited_once()


async def test_skippable_steps_do_not_block(env):
    async with env.client() as c:
        r = await c.post("/api/v1/onboarding/complete")
    assert r.status_code == 200


async def test_security_required_when_policy_covers(env):
    env.policy.get_policy.return_value = "everyone"
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


async def test_put_step_past_required_incomplete_400(env):
    env.repo.get_community.return_value = SimpleNamespace(
        onboarding_required=["birthday"], features={}
    )
    async with env.client() as c:
        blocked = await c.put("/api/v1/onboarding", json={"step": 2})
        ok = await c.put("/api/v1/onboarding", json={"step": 1})
    assert blocked.status_code == 400
    assert blocked.json()["error"]["code"] == "onboarding_step_incomplete"
    assert blocked.json()["error"]["details"]["missing"] == ["birthday"]
    assert ok.status_code == 200


async def test_security_now_past_grace(env):
    env.policy.get_policy.return_value = "everyone"
    past = datetime.now(UTC) - timedelta(days=8)
    async with env.client(two_factor_required_since=past) as c:
        late = (await c.get("/api/v1/onboarding")).json()
    async with env.client(two_factor_required_since=datetime.now(UTC)) as c:
        fresh = (await c.get("/api/v1/onboarding")).json()
    assert late["security_now"] is True
    assert fresh["security_now"] is False


async def test_complete_again_is_noop(env):
    done_at = datetime(2026, 1, 1, tzinfo=UTC)
    env.repo.get_community.return_value = SimpleNamespace(
        onboarding_required=["birthday"], features={}
    )
    async with env.client(onboarding_done_at=done_at) as c:
        r = await c.post("/api/v1/onboarding/complete")
        s = await c.put("/api/v1/onboarding", json={"step": 5})
    assert r.status_code == 200 and r.json()["done"] is True
    assert s.status_code == 200
    env.repo.mark_done.assert_not_awaited()
    env.repo.set_step.assert_not_awaited()


async def test_family_satisfied_by_household(env):
    env.repo.get_community.return_value = SimpleNamespace(
        onboarding_required=["family"], features={}
    )
    env.repo.has_family.return_value = True
    async with env.client() as c:
        r = await c.post("/api/v1/onboarding/complete")
    assert r.status_code == 200


async def test_family_not_required_when_relations_off(env):
    env.repo.get_community.return_value = SimpleNamespace(
        onboarding_required=["family"], features={"relations": False}
    )
    async with env.client() as c:
        s = await c.get("/api/v1/onboarding")
        r = await c.post("/api/v1/onboarding/complete")
    assert "family" not in s.json()["required"]
    assert r.status_code == 200


async def test_admin_cannot_require_family_when_relations_off(env):
    env.repo.get_community.return_value = SimpleNamespace(
        onboarding_required=[], features={"relations": False}
    )
    async with env.client("admin") as c:
        r = await c.put("/api/v1/admin/onboarding", json={"required": ["family"]})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "relations_disabled"
    env.repo.set_required.assert_not_awaited()
