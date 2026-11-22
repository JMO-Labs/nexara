"""
@file recap_sections.py
@brief Recap email section builders. ``SECTIONS`` is a plain list of async
       builders; later waves append (albums, recipes, story requests, chores).

Every builder reuses an existing viewer-aware service, so a recap never
contains anything the recipient could not open right now.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.features import is_enabled
from app.models.community import Community
from app.models.user import User
from app.repositories.album_repo import AlbumRepository
from app.repositories.celebration_repo import CelebrationRepository
from app.repositories.community_repo import CommunityRepository
from app.repositories.household_repo import HouseholdRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.post_memories_repo import PostMemoriesRepository
from app.repositories.recap_repo import RecapRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.time_capsule_repo import TimeCapsuleRepository
from app.repositories.user_repo import UserRepository
from app.services.celebration_service import CelebrationService
from app.services.memories_service import MemoriesService
from app.services.notification_service import NotificationService
from app.services.time_capsule_service import TimeCapsuleService

SNIPPET = 140
"""@brief Max characters of post text shown in the email."""


class RecapSection(TypedDict):
    """@brief One headed block: ``items`` are ``{"text": str, "link": str}``."""

    key: str
    title: str
    items: list[dict[str, Any]]


@dataclass
class RecapContext:
    """@brief Everything a section builder needs for one recipient."""

    user: User
    community: Community
    session: AsyncSession
    now: datetime
    today: date
    tz: str | None


SectionBuilder = Callable[[RecapContext], Awaitable[RecapSection | None]]


def snippet(text: str, limit: int = SNIPPET) -> str:
    """@return ``text`` flattened to one line and cut at ``limit`` characters."""
    flat = " ".join((text or "").split())
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"


def _ago(n: int) -> str:
    return "1 year ago" if n == 1 else f"{n} years ago"


async def on_this_day(ctx: RecapContext) -> RecapSection | None:
    """@brief Memories from today's month/day in past years (viewer-visible only)."""
    if not is_enabled(ctx.community, "on_this_day"):
        return None
    svc = MemoriesService(
        PostMemoriesRepository(ctx.session),
        UserRepository(ctx.session),
        CommunityRepository(ctx.session),
        ctx.community.id,
    )
    out = await svc.on_this_day(ctx.user.id, now=ctx.now)
    items = [
        {"text": f"{_ago(a)}: {snippet(p['content'])}", "link": f"/app/post/{p['id']}"}
        for p, a in zip(out["items"], out["years_ago"], strict=False)
    ]
    return {"key": "on_this_day", "title": "On this day", "items": items}


async def daily_question(ctx: RecapContext) -> RecapSection | None:
    """@brief Yesterday's community question and how many people answered."""
    if not is_enabled(ctx.community, "daily_question"):
        return None
    found = await RecapRepository(ctx.session).yesterday_daily(
        ctx.community.id, ctx.today - timedelta(days=1)
    )
    if found is None:
        return None
    post_id, text, count = found
    noun = "answer" if count == 1 else "answers"
    item = {"text": f"{snippet(text)} ({count} {noun})", "link": f"/app/post/{post_id}"}
    return {"key": "daily_question", "title": "Yesterday's question", "items": [item]}


async def birthdays(ctx: RecapContext) -> RecapSection | None:
    """@brief Birthdays in the next 7 days (as the viewer may see them)."""
    svc = CelebrationService(
        CelebrationRepository(ctx.session), HouseholdRepository(ctx.session), ctx.community.id
    )
    found = await svc.in_range(ctx.user, ctx.today, ctx.today + timedelta(days=6))
    items = [
        {"text": f"{c.name}, {c.date.strftime('%A %b')} {c.date.day}", "link": c.link}
        for c in found
        if c.occasion == "birthday"
    ]
    return {"key": "birthdays", "title": "Birthdays this week", "items": items}


async def capsules_opened(ctx: RecapContext) -> RecapSection | None:
    """@brief Time capsules addressed to the viewer that opened in the last 7 days."""
    if not is_enabled(ctx.community, "time_capsules"):
        return None
    svc = TimeCapsuleService(
        TimeCapsuleRepository(ctx.session),
        CommunityRepository(ctx.session),
        NotificationService(
            NotificationRepository(ctx.session),
            SettingsRepository(ctx.session),
            ctx.community.id,
        ),
        ctx.community.id,
    )
    since = ctx.now - timedelta(days=7)
    items = [
        {
            "text": f"{c.title}, from {c.author.display_name}",
            "link": f"/app/capsules/{c.id}",
        }
        for c in (await svc.list_for_viewer(ctx.user.id))["opened"]
        if c.opened_at is not None and c.opened_at >= since
    ]
    return {"key": "capsules", "title": "Time capsules opened", "items": items}


async def new_albums(ctx: RecapContext) -> RecapSection | None:
    """@brief Event albums with photos created in the last 7 days (viewer-visible only)."""
    if not is_enabled(ctx.community, "event_albums"):
        return None
    found = await AlbumRepository(ctx.session).new_event_galleries(
        ctx.community.id, ctx.user.id, ctx.now - timedelta(days=7)
    )
    items = [{"text": g.title, "link": f"/app/photos?gallery={g.id}"} for g in found]
    return {"key": "new_albums", "title": "New photo albums", "items": items}


SECTIONS: list[SectionBuilder] = [
    on_this_day,
    daily_question,
    birthdays,
    capsules_opened,
    new_albums,
]
"""@brief Ordered section builders; append new ones here."""
