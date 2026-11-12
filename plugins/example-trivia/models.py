"""
@file models.py
@brief Trivia data models and business logic, stored in ``plugin_data`` via ``ctx.db``.

Keys: ``question:today``, ``questions:bank``, ``answer:<date>:<user>``,
``stats:<user>`` and ``stats:index`` (list of user ids with stats).
"""

from __future__ import annotations

import random
import uuid
from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel, Field

LEADERBOARD_MAX = 100

DEFAULT_BANK: list[dict[str, Any]] = [
    {"text": "Which planet is known as the Red Planet?",
     "options": ["Venus", "Mars", "Jupiter", "Mercury"], "correct_index": 1},
    {"text": "How many continents are there?",
     "options": ["Five", "Six", "Seven", "Eight"], "correct_index": 2},
    {"text": "What is the largest ocean on Earth?",
     "options": ["Atlantic", "Indian", "Arctic", "Pacific"], "correct_index": 3},
    {"text": "Which gas do plants absorb from the air?",
     "options": ["Carbon dioxide", "Oxygen", "Nitrogen", "Helium"], "correct_index": 0},
    {"text": "What is the capital of Japan?",
     "options": ["Osaka", "Kyoto", "Tokyo", "Nagoya"], "correct_index": 2},
    {"text": "How many sides does a hexagon have?",
     "options": ["Five", "Six", "Seven", "Eight"], "correct_index": 1},
]  # fmt: skip


class AlreadyAnsweredError(ValueError):
    """@brief The user already answered today's question."""


class TriviaQuestion(BaseModel):
    """@brief A multiple-choice question: 4 options, one correct."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    text: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    date: str | None = None


class UserAnswer(BaseModel):
    """@brief One user's answer to one day's question."""

    user_id: str
    question_id: str
    answer_text: str
    correct: bool
    date: str


class UserStats(BaseModel):
    """@brief Per-user counters; ``last_correct_date`` drives streak continuity."""

    streak: int = 0
    total_correct: int = 0
    last_correct_date: str | None = None


def _effective_streak(stats: UserStats, today: date) -> int:
    """@brief Streak still alive on ``today`` (0 once a whole day was missed)."""
    if stats.last_correct_date is None:
        return 0
    if date.fromisoformat(stats.last_correct_date) < today - timedelta(days=1):
        return 0
    return stats.streak


async def _load_stats(ctx: Any, user_id: str) -> UserStats:
    raw = await ctx.db.get(f"stats:{user_id}")
    return UserStats(**raw) if raw else UserStats()


async def select_daily_question(
    ctx: Any, today: date, rng: random.Random | None = None
) -> dict[str, Any]:
    """
    @brief Pick a random question (never yesterday's) and store it as ``question:today``.
    @return The stored question including the answer key.
    """
    rng = rng or random.Random()
    bank = await ctx.db.get("questions:bank") or DEFAULT_BANK
    current = await ctx.db.get("question:today")
    pool = [q for q in bank if not current or q["text"] != current["text"]] or bank
    picked = TriviaQuestion(**rng.choice(pool), date=today.isoformat())
    question = picked.model_dump()
    await ctx.db.set("question:today", question)
    return question


async def get_today_public(ctx: Any) -> dict[str, Any] | None:
    """@brief Today's question without the answer key, or None."""
    q = await ctx.db.get("question:today")
    if not q:
        return None
    return {k: q[k] for k in ("id", "text", "options", "date")}


async def submit_answer(
    ctx: Any, user_id: str, question_id: str, answer_text: str, today: date
) -> dict[str, Any]:
    """
    @brief Score an answer and update stats/streak.
    @throws ValueError if the question is not today's; AlreadyAnsweredError on repeat.
    """
    q = await ctx.db.get("question:today")
    if not q or q["id"] != question_id or q.get("date") != today.isoformat():
        raise ValueError("Question is not today's question")
    akey = f"answer:{today.isoformat()}:{user_id}"
    if await ctx.db.get(akey):
        raise AlreadyAnsweredError("Already answered today")
    correct = answer_text.strip().casefold() == q["options"][q["correct_index"]].casefold()
    await ctx.db.set(
        akey,
        UserAnswer(
            user_id=user_id, question_id=question_id, answer_text=answer_text,
            correct=correct, date=today.isoformat(),
        ).model_dump(),
    )  # fmt: skip
    stats = await _load_stats(ctx, user_id)
    if correct:
        stats.streak = _effective_streak(stats, today) + 1
        stats.total_correct += 1
        stats.last_correct_date = today.isoformat()
    await ctx.db.set(f"stats:{user_id}", stats.model_dump())
    index = await ctx.db.get("stats:index") or []
    if user_id not in index:
        await ctx.db.set("stats:index", [*index, user_id])
    return {
        "correct": correct,
        "correct_option": q["options"][q["correct_index"]],
        "streak": _effective_streak(stats, today),
        "total_correct": stats.total_correct,
    }


async def _ranked(ctx: Any, today: date) -> list[dict[str, Any]]:
    rows = []
    for uid in await ctx.db.get("stats:index") or []:
        s = await _load_stats(ctx, uid)
        rows.append(
            {"user_id": uid, "streak": _effective_streak(s, today),
             "total_correct": s.total_correct}
        )  # fmt: skip
    rows.sort(key=lambda r: (-r["streak"], -r["total_correct"], r["user_id"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


async def leaderboard(ctx: Any, today: date, page: int = 1, size: int = 20) -> dict[str, Any]:
    """@brief Paginated top-100 by streak, then total correct."""
    rows = (await _ranked(ctx, today))[:LEADERBOARD_MAX]
    start = (page - 1) * size
    return {"items": rows[start : start + size], "total": len(rows), "page": page, "size": size}


async def my_stats(ctx: Any, user_id: str, today: date) -> dict[str, Any]:
    """@brief Streak, total correct and rank (None when the user never answered)."""
    s = await _load_stats(ctx, user_id)
    rank = next((r["rank"] for r in await _ranked(ctx, today) if r["user_id"] == user_id), None)
    return {"streak": _effective_streak(s, today), "total_correct": s.total_correct, "rank": rank}


async def reset_all_streaks(ctx: Any) -> int:
    """@brief Zero every user's streak (weekly job). @return Number of users reset."""
    index = await ctx.db.get("stats:index") or []
    for uid in index:
        s = await _load_stats(ctx, uid)
        s.streak = 0
        await ctx.db.set(f"stats:{uid}", s.model_dump())
    return len(index)
