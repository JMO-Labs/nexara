"""
@file test_admin_ai.py
@brief Integration tests for /api/v1/admin/ai (config, metrics, test-connection).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_admin_ai_service, get_current_user
from app.services.ai.admin_ai_service import AdminAIService
from app.services.ai.budget_service import BudgetService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 11, 12, 10, tzinfo=UTC)


class FakeRedis:
    """@brief Minimal in-memory async Redis (strings + hashes, honours expire)."""

    def __init__(self, clock=lambda: NOW) -> None:
        self.s: dict[str, str] = {}
        self.h: dict[str, dict[str, str]] = {}
        self.exp: dict[str, datetime] = {}
        self.clock = clock

    async def get(self, k):
        if k in self.exp and self.clock() >= self.exp[k]:
            return None
        return self.s.get(k)

    async def set(self, k, v):
        self.s[k] = v

    async def incrbyfloat(self, k, v):
        self.s[k] = str(float(self.s.get(k, 0)) + v)

    async def expire(self, k, seconds):
        self.exp[k] = self.clock() + timedelta(seconds=seconds)
        return True

    async def hincrbyfloat(self, k, f, v):
        d = self.h.setdefault(k, {})
        d[f] = str(float(d.get(f, 0)) + v)

    async def hgetall(self, k):
        return dict(self.h.get(k, {}))


class FakeCommunityRepo:
    """@brief In-memory stand-in for CommunityRepository (one community row)."""

    def __init__(self) -> None:
        self.row = SimpleNamespace(
            id=CID,
            sassybot_enabled=True,
            sassybot_sass_level=2,
            sassybot_probability=15,
            sassybot_invoke_only=False,
        )

    async def get(self, cid):
        return self.row if cid == CID else None

    async def update_sassybot(self, cid, values):
        if cid != CID:
            return None
        for k, v in values.items():
            setattr(self.row, k, v)
        return self.row


class FakeProvider:
    """@brief Provider whose ping succeeds or raises."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.pinged = 0

    async def ping(self):
        self.pinged += 1
        if self.fail:
            raise RuntimeError("boom")


@pytest.fixture
def env(test_app):
    now = SimpleNamespace(value=NOW)
    redis = FakeRedis(clock=lambda: now.value)
    community_repo = FakeCommunityRepo()
    settings_repo = MagicMock()
    settings_repo.count_sassybot_opt_outs = AsyncMock(return_value=3)
    audit_repo = MagicMock()
    audit_repo.append = AsyncMock()
    actor = uuid.uuid4()
    box = SimpleNamespace(provider=FakeProvider())
    settings = SimpleNamespace(
        AI_PROVIDER="ollama", AI_DAILY_BUDGET_CENTS=200, AI_BUDGET_RESET_HOUR=0
    )
    budget = BudgetService(redis, 200, clock=lambda: now.value)
    svc = AdminAIService(
        community_repo,
        settings_repo,
        CID,
        settings,
        budget,
        lambda: box.provider,
        audit_repo=audit_repo,
        actor_id=actor,
        ip_address="10.0.0.1",
    )
    test_app.dependency_overrides[get_admin_ai_service] = lambda: svc

    def client(role="admin"):
        user = SimpleNamespace(id=uuid.uuid4(), role=role, community_id=CID)
        test_app.dependency_overrides[get_current_user] = lambda: user
        return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")

    yield SimpleNamespace(
        now=now,
        client=client,
        budget=budget,
        box=box,
        community=community_repo,
        settings_repo=settings_repo,
        audit=audit_repo,
        actor=actor,
    )
    test_app.dependency_overrides.clear()


async def test_get_config_defaults(env):
    async with env.client() as c:
        r = await c.get("/api/v1/admin/ai/config")
    assert r.status_code == 200
    assert r.json() == {
        "provider": "ollama",
        "sassybot_enabled": True,
        "sass_level": 2,
        "probability": 15,
        "invoke_only": False,
        "opt_out_count": 3,
    }


async def test_opt_out_count_scoped_to_community(env):
    async with env.client() as c:
        await c.get("/api/v1/admin/ai/config")
    env.settings_repo.count_sassybot_opt_outs.assert_awaited_with(CID)


async def test_put_config_persists(env):
    async with env.client() as c:
        r = await c.put(
            "/api/v1/admin/ai/config",
            json={
                "sassybot_enabled": False,
                "sass_level": 3,
                "probability": 55,
                "invoke_only": True,
            },
        )
        assert r.status_code == 200
        assert r.json()["sass_level"] == 3
        got = (await c.get("/api/v1/admin/ai/config")).json()
    assert got["sassybot_enabled"] is False
    assert got["probability"] == 55
    assert got["invoke_only"] is True
    row = env.community.row
    assert row.sassybot_enabled is False
    assert row.sassybot_sass_level == 3
    assert row.sassybot_probability == 55
    assert row.sassybot_invoke_only is True
    kw = env.audit.append.await_args.kwargs
    assert kw["action"] == "ai.config.updated"
    assert kw["actor_id"] == env.actor and kw["target_id"] == CID
    assert kw["ip_address"] == "10.0.0.1"


async def test_empty_put_does_not_audit(env):
    async with env.client() as c:
        r = await c.put("/api/v1/admin/ai/config", json={})
    assert r.status_code == 200
    env.audit.append.assert_not_awaited()


@pytest.mark.parametrize(
    "body", [{"sass_level": 4}, {"sass_level": 0}, {"probability": 101}, {"probability": -1}]
)
async def test_put_config_validates(env, body):
    async with env.client() as c:
        r = await c.put("/api/v1/admin/ai/config", json=body)
    assert r.status_code == 422


async def test_non_admin_forbidden(env):
    async with env.client("member") as c:
        assert (await c.get("/api/v1/admin/ai/config")).status_code == 403
        assert (await c.get("/api/v1/admin/ai/metrics")).status_code == 403


async def test_metrics_calculation(env):
    await env.budget.record_usage(30, "ocr")
    await env.budget.record_usage(20, "sassybot")
    await env.budget.record_usage(10, "sassybot")
    async with env.client() as c:
        r = await c.get("/api/v1/admin/ai/metrics")
    body = r.json()
    assert body["daily_usage_cents"] == 60
    assert body["daily_budget_cents"] == 200
    assert len(body["last_7_days"]) == 7
    assert body["last_7_days"][-1] == {"date": "2026-11-12", "cents": 60}
    assert body["last_7_days"][0]["cents"] == 0
    rows = {b["feature"]: b for b in body["breakdown"]}
    assert rows["sassybot"] == {"feature": "sassybot", "calls": 2, "cents": 30}
    assert rows["ocr"] == {"feature": "ocr", "calls": 1, "cents": 30}
    assert rows["suggestion"] == {"feature": "suggestion", "calls": 0, "cents": 0}


async def test_metrics_include_earlier_days(env):
    env.now.value = NOW - timedelta(days=5)
    await env.budget.record_usage(42, "ocr")
    env.now.value = NOW
    async with env.client() as c:
        days = (await c.get("/api/v1/admin/ai/metrics")).json()["last_7_days"]
    assert days[1] == {"date": "2026-11-07", "cents": 42}
    assert days[-1]["cents"] == 0


async def test_test_connection_success_and_failure(env):
    async with env.client() as c:
        ok = (await c.post("/api/v1/admin/ai/test-connection")).json()
        pinged = env.box.provider.pinged
        env.box.provider = FakeProvider(fail=True)
        bad = (await c.post("/api/v1/admin/ai/test-connection")).json()
        env.box.provider = None
        none = (await c.post("/api/v1/admin/ai/test-connection")).json()
    assert ok["success"] is True and pinged == 1
    assert bad["success"] is False and "boom" not in bad["message"]
    assert none["success"] is False
