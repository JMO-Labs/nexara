"""
@file test_budget.py
@brief Unit tests for the AI daily budget service and cost calculation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError
from app.services.ai.budget_service import BudgetExceededError, BudgetService
from app.services.ai.ocr import run_ocr
from app.services.ai.provider import cost_cents
from tests.unit.services.ai.test_ocr import CID, _deps


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, float] = {}
        self.ttl: dict[str, int] = {}

    async def get(self, key: str):
        return str(self.data[key]) if key in self.data else None

    async def incrbyfloat(self, key: str, amount: float) -> float:
        self.data[key] = self.data.get(key, 0.0) + amount
        return self.data[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.ttl[key] = seconds

    async def delete(self, key: str) -> None:
        self.data.pop(key, None)


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
    assert r.ttl["ai_budget:2026-01-05:cents"] == 48 * 3600


async def test_check_budget_blocks_when_exhausted() -> None:
    svc, _ = _svc(budget=10)
    await svc.record_usage(10, "ocr")
    assert await svc.check_budget(1) is False
    assert await svc.check_budget(0) is True


async def test_check_budget_blocks_when_estimate_exceeds() -> None:
    svc, _ = _svc(budget=10)
    assert await svc.check_budget(11) is False
    assert await svc.check_budget(10) is True


async def test_reset_clears_today() -> None:
    svc, _ = _svc(budget=10)
    await svc.record_usage(10, "suggestion")
    await svc.reset_daily_budget()
    assert await svc.get_daily_budget() == 10


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
        uuid.uuid4(), CID, media_repo=media_repo, ai_repo=ai_repo, storage=storage,
        provider=provider, budget=budget,
    )
    assert status == "budget_exhausted"
    provider.vision.assert_not_called()


async def test_ocr_records_actual_cost() -> None:
    _, media_repo, ai_repo, storage, provider = _deps()
    budget = MagicMock()
    budget.check_budget = AsyncMock(return_value=True)
    budget.record_usage = AsyncMock()
    status = await run_ocr(
        uuid.uuid4(), CID, media_repo=media_repo, ai_repo=ai_repo, storage=storage,
        provider=provider, budget=budget,
    )
    assert status == "processed"
    assert budget.record_usage.await_args.args[:2] == (0.1, "ocr")
