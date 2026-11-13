"""
@file test_budget.py
@brief Unit tests for the AI daily budget service and cost calculation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from prometheus_client import REGISTRY

from app.core.exceptions import AppError
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.budget_service import BudgetExceededError, BudgetService
from app.services.ai.ocr import OCR_ESTIMATED_CENTS, run_ocr
from app.services.ai.ollama_provider import OllamaProvider
from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.provider import cost_cents
from tests.unit.services.ai.test_ocr import CID, _deps


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, float] = {}
        self.ttl: dict[str, int] = {}
        self.hashes: dict[str, dict[str, float]] = {}

    async def get(self, key: str):
        return str(self.data[key]) if key in self.data else None

    async def incrbyfloat(self, key: str, amount: float) -> float:
        self.data[key] = self.data.get(key, 0.0) + amount
        return self.data[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.ttl[key] = seconds

    async def delete(self, key: str) -> None:
        self.data.pop(key, None)

    async def hgetall(self, key: str) -> dict[str, float]:
        return dict(self.hashes.get(key, {}))

    async def hincrbyfloat(self, key: str, field: str, amount: float) -> float:
        self.hashes.setdefault(key, {})
        self.hashes[key][field] = self.hashes[key].get(field, 0.0) + amount
        return self.hashes[key][field]


def _svc(budget: int = 100, hour: int = 0, now: datetime | None = None):
    r = FakeRedis()
    clock = now or datetime(2026, 1, 5, 12, tzinfo=UTC)
    return BudgetService(r, budget, hour, clock=lambda: clock), r


async def test_remaining_starts_at_full_budget() -> None:
    svc, _ = _svc()
    assert await svc.get_daily_budget() == 100


async def test_record_usage_reduces_remaining_and_sets_ttl() -> None:
    svc, r = _svc()
    await svc.record_usage(30, "ocr")
    assert await svc.get_daily_budget() == 70
    assert r.ttl["ai_budget:2026-01-05:cents"] >= 7 * 24 * 3600
    assert r.ttl["ai_budget:2026-01-05:cents:features"] == 48 * 3600
    assert r.hashes["ai_budget:2026-01-05:cents:features"] == {
        "ocr:cents": 30,
        "ocr:calls": 1,
    }


async def test_check_budget_blocks_when_exhausted() -> None:
    svc, _ = _svc(budget=10)
    await svc.record_usage(10, "ocr")
    assert await svc.check_budget(1) is False
    assert await svc.check_budget(0) is True


async def test_check_budget_blocks_when_estimate_exceeds() -> None:
    svc, _ = _svc(budget=10)
    assert await svc.check_budget(11) is False
    assert await svc.check_budget(10) is True


@pytest.mark.parametrize("hour", [0, 6])
async def test_reset_at_boundary_keeps_current_day_spend(hour: int) -> None:
    now = datetime(2026, 1, 9, hour, 0, tzinfo=UTC)
    svc, r = _svc(budget=10, hour=hour, now=now)
    await svc.record_usage(4, "ocr")
    r.data["ai_budget:2026-01-08:cents"] = 9.0  # previous budget day
    r.data["ai_budget:2026-01-01:cents"] = 9.0  # outside the 7-day window
    await svc.reset_daily_budget()
    assert "ai_budget:2026-01-08:cents" in r.data  # kept for the chart
    assert "ai_budget:2026-01-01:cents" not in r.data
    assert await svc.get_daily_budget() == 6


async def test_day_boundary_honours_reset_hour() -> None:
    before, r = _svc(hour=6, now=datetime(2026, 1, 5, 5, 59, tzinfo=UTC))
    await before.record_usage(5, "ocr")
    assert "ai_budget:2026-01-04:cents" in r.data
    after = BudgetService(r, 100, 6, clock=lambda: datetime(2026, 1, 5, 6, 0, tzinfo=UTC))
    assert await after.get_daily_budget() == 100


def test_budget_exceeded_is_429_app_error() -> None:
    err = BudgetExceededError()
    assert isinstance(err, AppError)
    assert (err.code, err.status_code) == ("ai_budget_exceeded", 429)
    assert err.message == "Daily budget exhausted"


@pytest.mark.parametrize(
    ("in_rate", "out_rate", "expected"),
    [(0.25, 0.75, 100.0), (3.0, 15.0, 1800.0), (0.15, 0.60, 75.0), (0.0, 0.0, 0.0)],
)
def test_cost_per_model(in_rate: float, out_rate: float, expected: float) -> None:
    # 1M in + 1M out tokens; rates in USD/1M, result in cents
    assert cost_cents(1_000_000, 1_000_000, in_rate, out_rate) == pytest.approx(expected)


async def test_ocr_blocked_when_budget_exhausted() -> None:
    _, media_repo, ai_repo, storage, provider = _deps()
    budget = MagicMock()
    budget.check_budget = AsyncMock(return_value=False)
    budget.record_usage = AsyncMock()
    status = await run_ocr(
        uuid.uuid4(),
        CID,
        media_repo=media_repo,
        ai_repo=ai_repo,
        storage=storage,
        provider=provider,
        budget=budget,
    )
    assert status == "budget_exhausted"
    provider.vision.assert_not_called()


async def test_ocr_records_actual_cost() -> None:
    _, media_repo, ai_repo, storage, provider = _deps()
    budget = MagicMock()
    budget.check_budget = AsyncMock(return_value=True)
    budget.record_usage = AsyncMock()
    status = await run_ocr(
        uuid.uuid4(),
        CID,
        media_repo=media_repo,
        ai_repo=ai_repo,
        storage=storage,
        provider=provider,
        budget=budget,
    )
    assert status == "processed"
    assert budget.record_usage.await_args.args[:2] == (0.1, "ocr")


def _client(payload: dict) -> AsyncMock:
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    client = AsyncMock()
    client.post.return_value = resp
    return client


async def test_anthropic_vision_cost_uses_provider_pricing() -> None:
    usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    p = AnthropicProvider("k", client=_client({"content": [], "usage": usage}))
    _, cost, _ = await p.vision(b"\x89PNG", "x", 10)
    assert cost == pytest.approx(1800.0)  # sonnet 3 + 15 USD
    _, cost, _ = await p.complete("x", 10, 0.0)
    assert cost == pytest.approx(150.0)  # haiku 0.25 + 1.25 USD


async def test_openai_cost_uses_provider_pricing() -> None:
    usage = {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000}
    payload = {"choices": [{"message": {"content": "t"}}], "usage": usage}
    p = OpenAIProvider("k", client=_client(payload))
    _, cost, _ = await p.vision(b"\x89PNG", "x", 10)
    assert cost == pytest.approx(1250.0)  # gpt-4o 2.50 + 10 USD
    _, cost, _ = await p.complete("x", 10, 0.0)
    assert cost == pytest.approx(75.0)  # gpt-4o-mini 0.15 + 0.60 USD


async def test_ollama_cost_is_zero() -> None:
    payload = {"response": "t", "prompt_eval_count": 5, "eval_count": 5}
    p = OllamaProvider("http://o", "llava", client=_client(payload))
    _, cost, _ = await p.vision(b"img", "x", 10)
    assert cost == 0.0


def test_vision_model_names() -> None:
    assert AnthropicProvider("k").vision_model == "claude-3-sonnet-20240229"
    assert OpenAIProvider("k").vision_model == "gpt-4o"
    assert OllamaProvider("http://o", "llava").vision_model == "llava"


def _sample(name: str, **labels: str) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


async def test_record_usage_increments_prometheus() -> None:
    svc, _ = _svc()
    lb = {"model": "m-prom", "provider": "p-prom", "feature": "ocr"}
    cents0, calls0 = _sample("ai_usage_cents_total", **lb), _sample("ai_calls_total", **lb)
    await svc.record_usage(2.5, "ocr", provider="p-prom", model="m-prom")
    assert _sample("ai_usage_cents_total", **lb) == pytest.approx(cents0 + 2.5)
    assert _sample("ai_calls_total", **lb) == calls0 + 1


async def test_blocked_ocr_increments_exceeded_metric() -> None:
    _, media_repo, ai_repo, storage, provider = _deps()
    budget = MagicMock()
    budget.check_budget = AsyncMock(return_value=False)
    cid = uuid.uuid4()
    before = _sample("ai_budget_exceeded_total", community_id=str(cid))
    await run_ocr(
        uuid.uuid4(), cid, media_repo=media_repo, ai_repo=ai_repo,
        storage=storage, provider=provider, budget=budget,
    )  # fmt: skip
    assert _sample("ai_budget_exceeded_total", community_id=str(cid)) == before + 1


async def test_ocr_records_provider_vision_model() -> None:
    _, media_repo, ai_repo, storage, provider = _deps()
    provider.vision_model = "gpt-4o"
    budget = MagicMock()
    budget.check_budget = AsyncMock(return_value=True)
    budget.record_usage = AsyncMock()
    await run_ocr(
        uuid.uuid4(), CID, media_repo=media_repo, ai_repo=ai_repo,
        storage=storage, provider=provider, budget=budget,
    )  # fmt: skip
    assert budget.record_usage.await_args.kwargs["model"] == "gpt-4o"


def test_estimate_covers_worst_case_sonnet_vision() -> None:
    # 2000 output tokens at 15 USD/1M = 3 cents, plus image input headroom
    assert OCR_ESTIMATED_CENTS >= 3.5
