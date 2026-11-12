"""
@file test_trivia.py
@brief Integration tests for the example-trivia reference plugin.
"""

from __future__ import annotations

import importlib.util
import os
import random
import sys
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.dependencies import get_current_user
from app.models.user import User
from app.plugins.context import PluginContext
from app.plugins.manifest import load_manifest

PLUGIN_DIR = Path(__file__).resolve().parents[4] / "plugins" / "example-trivia"
TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
C1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
D0 = date(2026, 1, 1)


def _load(name: str):
    key = f"nexara_plugin_example_trivia_{name}"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, PLUGIN_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
async def session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


@pytest.fixture
def notifier() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def ctx(session, notifier) -> PluginContext:
    return PluginContext(
        "example-trivia", load_manifest(PLUGIN_DIR), session, C1, None, notifier
    )


async def _user(session: AsyncSession) -> User:
    tag = uuid.uuid4().hex[:8]
    u = User(community_id=C1, email=f"tv_{tag}@nexara.dev", username=f"tv_{tag}", display_name="T")
    session.add(u)
    await session.flush()
    return u


def test_manifest_declares_required_permissions():
    m = load_manifest(PLUGIN_DIR)
    assert {p.value for p in m.permissions} >= {
        "db_read", "db_write", "celery_tasks", "hooks_on_user_joined", "send_notifications",
    }
    assert "on_user_joined" in m.hooks


async def _today(ctx, day=D0, seed=1):
    models = _load("models")
    return await models.select_daily_question(ctx, day, random.Random(seed))


async def _correct(ctx, q) -> str:
    return q["options"][q["correct_index"]]


async def test_question_fetched_without_answer_key(ctx):
    models = _load("models")
    q = await _today(ctx)
    pub = await models.get_today_public(ctx)
    assert pub["id"] == q["id"] and len(pub["options"]) == 4
    assert "correct_index" not in pub


async def test_no_question_returns_none(ctx):
    assert await _load("models").get_today_public(ctx) is None


async def test_answer_scored_correct_and_wrong(ctx):
    models = _load("models")
    q = await _today(ctx)
    ok = await models.submit_answer(ctx, "u1", q["id"], await _correct(ctx, q), D0)
    assert ok["correct"] is True and ok["streak"] == 1
    wrong_opt = next(o for i, o in enumerate(q["options"]) if i != q["correct_index"])
    bad = await models.submit_answer(ctx, "u2", q["id"], wrong_opt, D0)
    assert bad["correct"] is False and bad["streak"] == 0


async def test_duplicate_and_stale_answer_rejected(ctx):
    models = _load("models")
    q = await _today(ctx)
    await models.submit_answer(ctx, "u1", q["id"], "x", D0)
    with pytest.raises(ValueError):
        await models.submit_answer(ctx, "u1", q["id"], "x", D0)
    with pytest.raises(ValueError):
        await models.submit_answer(ctx, "u3", "other-id", "x", D0)


async def test_streak_increments_on_consecutive_days_and_resets_on_miss(ctx):
    models = _load("models")
    for i in range(3):
        q = await _today(ctx, D0 + timedelta(days=i), seed=i)
        r = await models.submit_answer(
            ctx, "u1", q["id"], await _correct(ctx, q), D0 + timedelta(days=i)
        )
    assert r["streak"] == 3
    d = D0 + timedelta(days=5)  # skipped days 3 and 4
    q = await _today(ctx, d, seed=9)
    r = await models.submit_answer(ctx, "u1", q["id"], await _correct(ctx, q), d)
    assert r["streak"] == 1
    stats = await models.my_stats(ctx, "u1", d + timedelta(days=3))
    assert stats["streak"] == 0 and stats["total_correct"] == 4


async def test_leaderboard_sorted_by_streak_then_total(ctx):
    models = _load("models")
    plan = {"a": [0, 1, 2], "b": [0, 1, 2, 3], "c": [0, 2, 3]}  # streaks at day 3: b=4, a=3, c=2
    for day in range(4):
        q = await _today(ctx, D0 + timedelta(days=day), seed=day)
        for uid, days in plan.items():
            if day in days:
                await models.submit_answer(
                    ctx, uid, q["id"], await _correct(ctx, q), D0 + timedelta(days=day)
                )
    rows = await models.leaderboard(ctx, D0 + timedelta(days=3), page=1, size=10)
    assert [r["user_id"] for r in rows["items"]] == ["b", "a", "c"]
    streaks = [(r["streak"], r["total_correct"]) for r in rows["items"]]
    assert streaks == sorted(streaks, reverse=True)
    assert rows["items"][0]["user_id"] == "b" and rows["items"][0]["rank"] == 1


async def test_leaderboard_pagination_and_cap(ctx):
    models = _load("models")
    q = await _today(ctx)
    for i in range(5):
        await models.submit_answer(ctx, f"u{i}", q["id"], await _correct(ctx, q), D0)
    page2 = await models.leaderboard(ctx, D0, page=2, size=2)
    assert len(page2["items"]) == 2 and page2["total"] == 5 and page2["items"][0]["rank"] == 3
    assert models.LEADERBOARD_MAX == 100


async def test_my_stats_rank(ctx):
    models = _load("models")
    q = await _today(ctx)
    await models.submit_answer(ctx, "u1", q["id"], await _correct(ctx, q), D0)
    s = await models.my_stats(ctx, "u1", D0)
    assert s == {"streak": 1, "total_correct": 1, "rank": 1}
    empty = await models.my_stats(ctx, "nobody", D0)
    assert empty["rank"] is None and empty["streak"] == 0


async def test_daily_task_selects_new_question(ctx):
    models = _load("models")
    first = await _today(ctx, D0, seed=1)
    seen = {first["id"]}
    for i in range(1, 6):
        q = await models.select_daily_question(ctx, D0 + timedelta(days=i), random.Random(i))
        assert q["date"] == (D0 + timedelta(days=i)).isoformat()
        seen.add(q["id"])
    assert len(seen) > 1
    again = await models.select_daily_question(ctx, D0 + timedelta(days=5), random.Random(0))
    assert again["id"] != q["id"]  # never repeats the previous question


async def test_reset_streaks_zeroes_all(ctx):
    models = _load("models")
    q = await _today(ctx)
    await models.submit_answer(ctx, "u1", q["id"], await _correct(ctx, q), D0)
    assert await models.reset_all_streaks(ctx) == 1
    assert (await models.my_stats(ctx, "u1", D0))["streak"] == 0
    assert (await models.my_stats(ctx, "u1", D0))["total_correct"] == 1


async def test_on_user_joined_sends_notification(ctx, session, notifier):
    models, hooks = _load("models"), _load("hooks")
    user = await _user(session)
    q = await _today(ctx)
    await hooks.on_user_joined(ctx, user_id=user.id)
    notifier.notify.assert_awaited_once()
    args = notifier.notify.await_args
    assert args.args[0] == user.id and args.args[1] == "system"
    assert q["text"] in args.args[2]["message"]


async def test_on_user_joined_without_question_is_noop(ctx, session, notifier):
    user = await _user(session)
    await _load("hooks").on_user_joined(ctx, user_id=user.id)
    notifier.notify.assert_not_awaited()


def test_celery_tasks_registered_and_executable():
    from app.tasks import plugin_tasks  # noqa: F401
    from app.tasks.celery_app import celery_app

    tasks = _load("tasks")
    for name in (
        "plugins.example_trivia.select_daily_question",
        "plugins.example_trivia.reset_streaks",
    ):
        assert name in celery_app.tasks
    sched = celery_app.conf.beat_schedule
    assert any(
        v["task"] == "plugins.example_trivia.select_daily_question" for v in sched.values()
    )
    assert any(v["task"] == "plugins.example_trivia.reset_streaks" for v in sched.values())
    with patch.object(tasks, "_select", new=AsyncMock(return_value={"id": "q1"})):
        assert tasks.select_daily_question.apply().get() == {"id": "q1"}


async def _client(ctx, user) -> AsyncClient:
    router = _load("router")
    app = FastAPI()
    app.include_router(router.router, prefix="/api/v1/plugins/example-trivia")
    app.dependency_overrides[router.get_ctx] = lambda: ctx
    app.dependency_overrides[get_current_user] = lambda: user
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def test_router_endpoints(ctx, session):
    user = await _user(session)
    q = await _today(ctx, datetime.now(UTC).date())
    async with await _client(ctx, user) as c:
        r = await c.get("/api/v1/plugins/example-trivia/questions/today")
        assert r.status_code == 200 and "correct_index" not in r.json()
        r = await c.post(
            "/api/v1/plugins/example-trivia/answers",
            json={"question_id": q["id"], "answer_text": q["options"][q["correct_index"]]},
        )
        assert r.status_code == 200 and r.json()["correct"] is True
        again = await c.post(
            "/api/v1/plugins/example-trivia/answers",
            json={"question_id": q["id"], "answer_text": "x"},
        )
        assert again.status_code == 409
        r = await c.get("/api/v1/plugins/example-trivia/leaderboard?page=1&size=10")
        assert r.json()["items"][0]["user_id"] == str(user.id)
        r = await c.get("/api/v1/plugins/example-trivia/my-stats")
        assert r.json() == {"streak": 1, "total_correct": 1, "rank": 1}
