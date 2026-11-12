"""
@file admin_ai_service.py
@brief Admin AI configuration (Sassybot settings), usage metrics and connection test.

Settings are stored as a Valkey hash ``ai_config:<community_id>``; the provider
itself is chosen by the ``AI_PROVIDER`` env var and is read-only here.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, select

from app.models.user_settings import UserSettings
from app.services.ai.budget_service import BudgetService

logger = structlog.get_logger(__name__)

FEATURES = ("ocr", "suggestion", "sassybot")
DEFAULTS: dict[str, Any] = {
    "sassybot_enabled": True,
    "sass_level": 2,
    "probability": 20,
    "invoke_only": False,
}


def _decode(v: Any) -> str:
    return v.decode() if isinstance(v, bytes) else str(v)


class AdminAIService:
    """@brief Reads/writes AI admin config and computes usage metrics."""

    def __init__(
        self,
        redis: Any,
        session: Any,
        community_id: uuid.UUID,
        settings: Any,
        budget: BudgetService,
        provider_factory: Callable[[], Any],
        *,
        clock: Callable[[], datetime] | None = None,
        audit: Callable[..., Awaitable[None]] | None = None,
    ) -> None:
        """
        @param redis Async Redis client.
        @param session Async DB session (opt-out count).
        @param community_id Tenant id.
        @param settings App settings (provider, budget).
        @param budget Budget meter.
        @param provider_factory Returns the AI provider or None.
        @param clock now() override (tests).
        @param audit Async callable ``(action, extra)`` recording an audit entry.
        """
        self._redis = redis
        self._session = session
        self._cid = community_id
        self._settings = settings
        self._budget = budget
        self._provider_factory = provider_factory
        self._clock = clock or (lambda: datetime.now(UTC))
        self._audit = audit

    @property
    def _key(self) -> str:
        return f"ai_config:{self._cid}"

    async def _opt_out_count(self) -> int:
        stmt = (
            select(func.count())
            .select_from(UserSettings)
            .where(
                UserSettings.community_id == self._cid,
                UserSettings.allow_sassybot.is_(False),
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def get_config(self) -> dict[str, Any]:
        """@return Provider, Sassybot settings and opt-out count."""
        raw = {_decode(k): _decode(v) for k, v in (await self._redis.hgetall(self._key)).items()}
        cfg = dict(DEFAULTS)
        for k, default in DEFAULTS.items():
            if k in raw:
                cfg[k] = raw[k] == "1" if isinstance(default, bool) else int(raw[k])
        return {
            "provider": (self._settings.AI_PROVIDER or "").lower(),
            **cfg,
            "opt_out_count": await self._opt_out_count(),
        }

    async def update_config(self, changes: dict[str, Any]) -> dict[str, Any]:
        """
        @param changes Validated partial update of Sassybot settings.
        @return The updated config.
        """
        if changes:
            mapping = {k: int(v) if isinstance(v, bool) else v for k, v in changes.items()}
            await self._redis.hset(self._key, mapping=mapping)
            if self._audit:
                await self._audit("ai.config.updated", changes)
        return await self.get_config()

    async def get_metrics(self) -> dict[str, Any]:
        """@return Today's usage, budget, 7-day series and per-feature breakdown."""
        days = [
            {"date": self._budget.budget_day(i), "cents": round(await self._budget.spent_cents(i))}
            for i in range(6, -1, -1)
        ]
        totals = await self._budget.feature_totals()
        breakdown = [
            {
                "feature": f,
                "calls": int(totals.get(f, {}).get("calls", 0)),
                "cents": round(totals.get(f, {}).get("cents", 0)),
            }
            for f in FEATURES
        ]
        return {
            "daily_usage_cents": days[-1]["cents"],
            "daily_budget_cents": self._settings.AI_DAILY_BUDGET_CENTS,
            "last_7_days": days,
            "breakdown": breakdown,
        }

    async def test_connection(self) -> dict[str, Any]:
        """@return ``{success, message}``; provider errors are logged, not leaked."""
        provider = self._provider_factory()
        if provider is None:
            return {"success": False, "message": "No AI provider is configured"}
        try:
            await provider.count_tokens("ping")
        except Exception as exc:  # noqa: BLE001 - any provider failure means "not reachable"
            logger.warning("ai_test_connection_failed", error=type(exc).__name__)
            return {"success": False, "message": "Could not reach the AI provider"}
        return {"success": True, "message": "Connection successful"}
