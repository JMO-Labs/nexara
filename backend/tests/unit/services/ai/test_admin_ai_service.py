"""
@file test_admin_ai_service.py
@brief Unit tests for AdminAIService and the BudgetService history helpers.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import NotFoundError
from app.models.community import Community
from app.services.ai.admin_ai_service import AdminAIService
from tests.unit.services.ai.test_budget import _svc

CID = uuid.uuid4()
ACTOR = uuid.uuid4()


def _community() -> MagicMock:
    c = MagicMock(spec=Community)
    c.sassybot_enabled = True
    c.sassybot_sass_level = 2
    c.sassybot_probability = 10
    c.sassybot_invoke_only = False
    return c


def _service(community=None, *, audit=True, provider=None, budget=None):
    repo = AsyncMock()
    repo.get.return_value = community
    repo.update_sassybot.return_value = community
    settings_repo = AsyncMock()
    settings_repo.count_sassybot_opt_outs.return_value = 5
    settings = MagicMock(AI_PROVIDER="OpenAI", AI_DAILY_BUDGET_CENTS=100)
    audit_repo = AsyncMock() if audit else None
    svc = AdminAIService(
        repo,
        settings_repo,
        CID,
        settings,
        budget or _svc()[0],
        lambda: provider,
        audit_repo=audit_repo,
        actor_id=ACTOR,
        ip_address="1.2.3.4",
    )
    return svc, repo, audit_repo


@pytest.mark.asyncio
async def test_get_config_serializes():
    svc, _, _ = _service(_community())
    assert await svc.get_config() == {
        "provider": "openai",
        "sassybot_enabled": True,
        "sass_level": 2,
        "probability": 10,
        "invoke_only": False,
        "opt_out_count": 5,
    }


@pytest.mark.asyncio
async def test_get_config_missing_community():
    svc, _, _ = _service(None)
    with pytest.raises(NotFoundError):
        await svc.get_config()


@pytest.mark.asyncio
async def test_update_maps_fields_and_audits():
    svc, repo, audit = _service(_community())
    out = await svc.update_config({"sass_level": 3})
    repo.update_sassybot.assert_awaited_once_with(CID, {"sassybot_sass_level": 3})
    audit.append.assert_awaited_once_with(
        actor_id=ACTOR,
        action="ai.config.updated",
        target_type="community",
        target_id=CID,
        extra_data={"sass_level": 3},
        ip_address="1.2.3.4",
    )
    assert out["opt_out_count"] == 5


@pytest.mark.asyncio
async def test_update_without_audit_repo():
    svc, repo, _ = _service(_community(), audit=False)
    await svc.update_config({"probability": 50})
    repo.update_sassybot.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_empty_changes_returns_config():
    svc, repo, _ = _service(_community())
    out = await svc.update_config({})
    repo.update_sassybot.assert_not_awaited()
    assert out["sass_level"] == 2


@pytest.mark.asyncio
async def test_update_missing_community():
    svc, repo, audit = _service(None)
    with pytest.raises(NotFoundError):
        await svc.update_config({"sassybot_enabled": False})
    audit.append.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_metrics_series_and_breakdown():
    budget, _ = _svc(budget=100, now=datetime(2026, 1, 5, 12, tzinfo=UTC))
    await budget.record_usage(30, "ocr")
    await budget.record_usage(12, "sassybot")
    svc, _, _ = _service(_community(), budget=budget)
    metrics = await svc.get_metrics()
    assert metrics["daily_usage_cents"] == 42
    assert metrics["daily_budget_cents"] == 100
    assert [d["date"] for d in metrics["last_7_days"]][-1] == "2026-01-05"
    assert len(metrics["last_7_days"]) == 7
    assert metrics["breakdown"] == [
        {"feature": "ocr", "calls": 1, "cents": 30},
        {"feature": "suggestion", "calls": 0, "cents": 0},
        {"feature": "sassybot", "calls": 1, "cents": 12},
    ]


@pytest.mark.asyncio
async def test_test_connection_no_provider():
    svc, _, _ = _service(_community())
    assert (await svc.test_connection())["success"] is False


@pytest.mark.asyncio
async def test_test_connection_ok():
    provider = AsyncMock()
    svc, _, _ = _service(_community(), provider=provider)
    assert await svc.test_connection() == {"success": True, "message": "Connection successful"}
    provider.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_test_connection_failure_does_not_leak():
    provider = AsyncMock()
    provider.ping.side_effect = RuntimeError("secret-key-sk-123")
    svc, _, _ = _service(_community(), provider=provider)
    out = await svc.test_connection()
    assert out["success"] is False
    assert "secret" not in out["message"]


@pytest.mark.asyncio
async def test_budget_history_and_feature_totals_decode_bytes():
    budget, redis = _svc(now=datetime(2026, 1, 5, 12, tzinfo=UTC))
    assert budget.budget_day(2) == "2026-01-03"
    redis.data["ai_budget:2026-01-03:cents"] = 7.0
    assert await budget.spent_cents(2) == 7.0
    assert await budget.spent_cents(1) == 0.0

    async def hgetall(_key):
        return {b"ocr:calls": b"2", "ocr:cents": "9"}

    redis.hgetall = hgetall
    assert await budget.feature_totals() == {"ocr": {"calls": 2.0, "cents": 9.0}}
