"""
@file budget_service.py
@brief Daily AI spend cap tracked in Valkey (``ai_budget:YYYY-MM-DD:cents``).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.exceptions import AppError
from app.core.metrics import ai_calls_total, ai_usage_cents_total

HISTORY_DAYS = 7
"""@brief Budget days kept for the admin 7-day usage chart."""
KEY_TTL_SECONDS = (HISTORY_DAYS + 1) * 24 * 3600
"""@brief TTL of the daily cents key; must outlive the chart window."""
FEATURE_TTL_SECONDS = 48 * 3600
"""@brief TTL of the per-feature hash (only today's breakdown is shown)."""


class BudgetExceededError(AppError):
    """@brief Raised when the daily AI budget is exhausted (HTTP 429)."""

    def __init__(self) -> None:
        super().__init__(
            code="ai_budget_exceeded", message="Daily budget exhausted", status_code=429
        )


class BudgetService:
    """@brief Meters AI spend against a per-day budget in cents."""

    def __init__(
        self,
        redis: Any,
        daily_budget_cents: int,
        reset_hour: int = 0,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """
        @param redis Async Redis client.
        @param daily_budget_cents Budget per day in cents.
        @param reset_hour UTC hour at which the budget day rolls over.
        @param clock Optional now() override (tests).
        """
        self._redis = redis
        self._budget = daily_budget_cents
        self._reset_hour = reset_hour
        self._clock = clock or (lambda: datetime.now(UTC))

    def _key(self, days_back: int = 0) -> str:
        day = (self._clock() - timedelta(hours=self._reset_hour)).date()
        day -= timedelta(days=days_back)
        return f"ai_budget:{day.isoformat()}:cents"

    async def _spent(self) -> float:
        raw = await self._redis.get(self._key())
        return float(raw) if raw is not None else 0.0

    async def spent_cents(self, days_back: int = 0) -> float:
        """@return Cents spent on the budget day ``days_back`` days ago."""
        raw = await self._redis.get(self._key(days_back))
        return float(raw) if raw is not None else 0.0

    def budget_day(self, days_back: int = 0) -> str:
        """@return ISO date of the budget day ``days_back`` days ago."""
        return self._key(days_back).split(":")[1]

    async def feature_totals(self) -> dict[str, dict[str, float]]:
        """@return Today's ``{feature: {"calls", "cents"}}`` from the per-feature hash."""
        raw = await self._redis.hgetall(f"{self._key()}:features")
        out: dict[str, dict[str, float]] = {}
        for field, value in raw.items():
            name, _, kind = (field.decode() if isinstance(field, bytes) else field).rpartition(":")
            out.setdefault(name, {})[kind] = float(value)
        return out

    async def get_daily_budget(self) -> int:
        """@return Cents remaining today (never negative)."""
        return max(0, int(self._budget - await self._spent()))

    async def check_budget(self, estimated_cost_cents: float) -> bool:
        """@return True if the estimated cost fits in today's remaining budget."""
        spent = await self._spent()
        if estimated_cost_cents <= 0:
            return spent < self._budget or estimated_cost_cents == 0
        return spent + estimated_cost_cents <= self._budget

    async def record_usage(
        self,
        actual_cost_cents: float,
        feature: str,
        *,
        provider: str = "unknown",
        model: str = "unknown",
    ) -> None:
        """
        @brief Add actual spend to today's total and update Prometheus counters.
        @param feature One of ocr | suggestion | sassybot.
        """
        key = self._key()
        await self._redis.incrbyfloat(key, actual_cost_cents)
        await self._redis.expire(key, KEY_TTL_SECONDS)
        fkey = f"{key}:features"
        await self._redis.hincrbyfloat(fkey, f"{feature}:cents", actual_cost_cents)
        await self._redis.hincrbyfloat(fkey, f"{feature}:calls", 1)
        await self._redis.expire(fkey, FEATURE_TTL_SECONDS)
        labels = {"model": model, "provider": provider, "feature": feature}
        ai_usage_cents_total.labels(**labels).inc(actual_cost_cents)
        ai_calls_total.labels(**labels).inc()

    async def reset_daily_budget(self) -> None:
        """
        @brief Delete the counter that just left the history window (Beat job).
        @note Keys are date-scoped so rollover is automatic; the last
              ``HISTORY_DAYS`` days are kept for the admin usage chart.
        """
        await self._redis.delete(self._key(days_back=HISTORY_DAYS + 1))
