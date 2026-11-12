"""
@file test_ai_budget_tasks.py
@brief Unit tests for _ocr_async and reset_ai_daily_budget task bodies.
"""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from app.tasks import ai_tasks
from app.tasks.maintenance_tasks import reset_ai_daily_budget


class TestOcrAsync:
    """@brief Verify _ocr_async wiring, commit and pool cleanup."""

    async def test_runs_ocr_commits_and_closes_pool(self):
        redis = AsyncMock()
        session = AsyncMock()

        @asynccontextmanager
        async def factory():
            yield session

        with (
            patch.object(ai_tasks, "get_settings", return_value=MagicMock()),
            patch.object(ai_tasks, "create_pool", return_value=redis),
            patch.object(ai_tasks, "async_session_factory", factory),
            patch.object(ai_tasks, "BudgetService"),
            patch.object(ai_tasks, "MediaRepository"),
            patch.object(ai_tasks, "MediaAIRepository"),
            patch.object(ai_tasks, "get_storage_backend"),
            patch.object(ai_tasks, "get_ai_provider"),
            patch.object(ai_tasks, "run_ocr", AsyncMock(return_value="done")) as run,
        ):
            result = await ai_tasks._ocr_async(uuid.uuid4(), uuid.uuid4())

        assert result == "done"
        run.assert_awaited_once()
        session.commit.assert_awaited_once()
        redis.aclose.assert_awaited_once()

    async def test_pool_closed_when_ocr_raises(self):
        redis = AsyncMock()
        session = AsyncMock()

        @asynccontextmanager
        async def factory():
            yield session

        with (
            patch.object(ai_tasks, "get_settings", return_value=MagicMock()),
            patch.object(ai_tasks, "create_pool", return_value=redis),
            patch.object(ai_tasks, "async_session_factory", factory),
            patch.object(ai_tasks, "BudgetService"),
            patch.object(ai_tasks, "MediaRepository"),
            patch.object(ai_tasks, "MediaAIRepository"),
            patch.object(ai_tasks, "get_storage_backend"),
            patch.object(ai_tasks, "get_ai_provider"),
            patch.object(ai_tasks, "run_ocr", AsyncMock(side_effect=RuntimeError("x"))),
        ):
            try:
                await ai_tasks._ocr_async(uuid.uuid4(), uuid.uuid4())
            except RuntimeError:
                pass

        session.commit.assert_not_awaited()
        redis.aclose.assert_awaited_once()


class TestResetAiDailyBudget:
    """@brief Verify the reset task resets the budget and closes the pool."""

    def test_resets_budget_and_closes_pool(self):
        redis = AsyncMock()
        budget = MagicMock()
        budget.reset_daily_budget = AsyncMock()
        with (
            patch("app.core.config.get_settings", return_value=MagicMock()),
            patch("app.core.valkey.create_pool", return_value=redis),
            patch("app.services.ai.budget_service.BudgetService", return_value=budget),
        ):
            result = reset_ai_daily_budget()

        assert result == {"status": "reset"}
        budget.reset_daily_budget.assert_awaited_once()
        redis.aclose.assert_awaited_once()
