"""
@file admin_ai_service.py
@brief Admin AI configuration (Sassybot settings), usage metrics and connection test.

Sassybot settings live on the ``Community`` row (the same columns Sassybot reads);
the provider itself is chosen by the ``AI_PROVIDER`` env var and is read-only here.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import structlog

from app.core.exceptions import NotFoundError
from app.services.ai.budget_service import BudgetService

logger = structlog.get_logger(__name__)

FEATURES = ("ocr", "suggestion", "sassybot")
#: API field -> ``Community`` column.
FIELD_TO_COLUMN = {
    "sassybot_enabled": "sassybot_enabled",
    "sass_level": "sassybot_sass_level",
    "probability": "sassybot_probability",
    "invoke_only": "sassybot_invoke_only",
}


class AdminAIService:
    """@brief Reads/writes AI admin config and computes usage metrics."""

    def __init__(
        self,
        community_repo: Any,
        settings_repo: Any,
        community_id: uuid.UUID,
        settings: Any,
        budget: BudgetService,
        provider_factory: Callable[[], Any],
        *,
        audit_repo: Any | None = None,
        actor_id: uuid.UUID | None = None,
        ip_address: str | None = None,
    ) -> None:
        """
        @param community_repo CommunityRepository (Sassybot columns).
        @param settings_repo SettingsRepository (opt-out count).
        @param community_id Tenant id.
        @param settings App settings (provider, budget).
        @param budget Budget meter.
        @param provider_factory Returns the AI provider or None.
        @param audit_repo AuditRepository; config changes are recorded when set.
        @param actor_id Admin performing the request (audit).
        @param ip_address Client IP (audit).
        """
        self._communities = community_repo
        self._user_settings = settings_repo
        self._cid = community_id
        self._settings = settings
        self._budget = budget
        self._provider_factory = provider_factory
        self._audit = audit_repo
        self._actor_id = actor_id
        self._ip = ip_address

    def _serialize(self, community: Any, opt_outs: int) -> dict[str, Any]:
        return {
            "provider": (self._settings.AI_PROVIDER or "").lower(),
            **{field: getattr(community, col) for field, col in FIELD_TO_COLUMN.items()},
            "opt_out_count": opt_outs,
        }

    async def get_config(self) -> dict[str, Any]:
        """
        @return Provider, Sassybot settings and opt-out count.
        @throws NotFoundError if the community row is missing.
        """
        community = await self._communities.get(self._cid)
        if community is None:
            raise NotFoundError()
        opt_outs = await self._user_settings.count_sassybot_opt_outs(self._cid)
        return self._serialize(community, opt_outs)

    async def update_config(self, changes: dict[str, Any]) -> dict[str, Any]:
        """
        @param changes Validated partial update of Sassybot settings (API field names).
        @return The updated config.
        @throws NotFoundError if the community row is missing.
        """
        if not changes:
            return await self.get_config()
        values = {FIELD_TO_COLUMN[k]: v for k, v in changes.items()}
        community = await self._communities.update_sassybot(self._cid, values)
        if community is None:
            raise NotFoundError()
        if self._audit is not None:
            await self._audit.append(
                actor_id=self._actor_id,
                action="ai.config.updated",
                target_type="community",
                target_id=self._cid,
                extra_data=changes,
                ip_address=self._ip,
            )
        opt_outs = await self._user_settings.count_sassybot_opt_outs(self._cid)
        return self._serialize(community, opt_outs)

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
            await provider.ping()
        except Exception as exc:  # noqa: BLE001 - any provider failure means "not reachable"
            logger.warning("ai_test_connection_failed", error=type(exc).__name__)
            return {"success": False, "message": "Could not reach the AI provider"}
        return {"success": True, "message": "Connection successful"}
