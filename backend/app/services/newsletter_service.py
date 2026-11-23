"""
@file newsletter_service.py
@brief Auto-curated monthly newsletter, built per viewer. Posts, photos,
       recipes, events and capsules all come through viewer-aware predicates or
       services, so admin pins can reorder but never reveal anything.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.features import is_enabled, require_feature
from app.models.user import User
from app.repositories.celebration_repo import CelebrationRepository
from app.repositories.community_repo import CommunityRepository
from app.repositories.household_repo import HouseholdRepository
from app.repositories.newsletter_repo import PHOTOS, TOP_POSTS, NewsletterRepository, PostRow
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.time_capsule_repo import TimeCapsuleRepository
from app.schemas.newsletter import (
    NewsCapsule,
    NewsEvent,
    Newsletter,
    NewsPerson,
    NewsPhoto,
    NewsPost,
    NewsRecipe,
)
from app.services.celebration_service import CelebrationService
from app.services.notification_service import NotificationService
from app.services.time_capsule_service import TimeCapsuleService

EXCERPT = 400
_MONTH = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def _zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return ZoneInfo("UTC")


def parse_month(month: str) -> tuple[int, int]:
    """@raises NotFoundError for anything but ``YYYY-MM``."""
    m = _MONTH.match(month)
    if m is None:
        raise NotFoundError()
    return int(m[1]), int(m[2])


def month_bounds(month: str, tz: str | None) -> tuple[datetime, datetime]:
    """@return ``[start, end)`` as UTC datetimes, with month edges in ``tz``."""
    y, m = parse_month(month)
    zone = _zone(tz)
    nxt = (y + (m == 12), m % 12 + 1)
    start = datetime(y, m, 1, tzinfo=zone).astimezone(UTC)
    return start, datetime(nxt[0], nxt[1], 1, tzinfo=zone).astimezone(UTC)


def check_month(month: str, tz: str | None, created: datetime, now: datetime) -> None:
    """@raises NotFoundError when the month is in the future or before the community began."""
    y, m = parse_month(month)
    zone = _zone(tz)
    cur, first = now.astimezone(zone), created.astimezone(zone)
    if (y, m) > (cur.year, cur.month) or (y, m) < (first.year, first.month):
        raise NotFoundError()


def _excerpt(text: str) -> str:
    flat = " ".join((text or "").split())
    return flat if len(flat) <= EXCERPT else flat[: EXCERPT - 1].rstrip() + "…"


def _news_post(r: PostRow, media: list[uuid.UUID]) -> NewsPost:
    return NewsPost(
        id=r.post.id,
        author_name=r.author_name,
        excerpt=_excerpt(r.post.content),
        created_at=r.post.created_at,
        reactions=r.reactions,
        comments=r.comments,
        pinned=r.action == "pin",
        media_ids=media[:1],
    )


class NewsletterService:
    """@brief Builds the newsletter and stores admin overrides."""

    def __init__(self, session: AsyncSession, community_id: uuid.UUID) -> None:
        self._session = session
        self._cid = community_id
        self._repo = NewsletterRepository(session, community_id)

    async def build(self, month: str, viewer: User, now: datetime | None = None) -> Newsletter:
        """
        @param month ``YYYY-MM``; not in the future and not before the community began.
        @param viewer The reader; every section is filtered for them.
        @raises NotFoundError for a bad, future or too-early month, or flag off.
        """
        community = await CommunityRepository(self._session).get(self._cid)
        if community is None:
            raise NotFoundError()
        require_feature(community, "newsletter")
        check_month(month, viewer.timezone, community.created_at, now or datetime.now(UTC))
        start, end = month_bounds(month, viewer.timezone)
        rows = await self._repo.month_posts(viewer.id, start, end, month)
        shown = [r for r in rows if r.action != "hide"]
        shown.sort(key=lambda r: r.action != "pin")  # stable: score order kept
        media: dict[uuid.UUID, list[tuple[uuid.UUID, str | None]]] = {}
        for pid, mid, alt in await self._repo.post_media([r.post.id for r in shown]):
            media.setdefault(pid, []).append((mid, alt))
        top = [_news_post(r, [m for m, _ in media.get(r.post.id, [])]) for r in shown[:TOP_POSTS]]
        photos = [
            NewsPhoto(media_id=mid, post_id=r.post.id, alt=alt)
            for r in shown
            for mid, alt in media.get(r.post.id, [])
        ][:PHOTOS]
        hidden = (
            [_news_post(r, []) for r in rows if r.action == "hide"]
            if viewer.role == "admin"
            else []
        )
        local = _zone(viewer.timezone)
        first, last = start.astimezone(local).date(), end.astimezone(local).date()
        people = await self._people(viewer, first, last)
        return Newsletter(
            month=month,
            community_name=community.name,
            top_posts=top,
            photos=photos,
            birthdays=[p for kind, p in people if kind == "birthday"],
            remembrances=[p for kind, p in people if kind == "remembrance"],
            new_recipes=await self._recipes(community, viewer, start, end),
            opened_capsules=await self._capsules(community, viewer, start, end),
            events=await self._events(viewer, start, end, local),
            hidden_posts=hidden,
        )

    async def _people(self, viewer: User, first: date, last: date) -> list[tuple[str, NewsPerson]]:
        svc = CelebrationService(
            CelebrationRepository(self._session), HouseholdRepository(self._session), self._cid
        )
        community = await CommunityRepository(self._session).get(self._cid)
        memorials = community is not None and is_enabled(community, "memorials")
        last_day = date.fromordinal(last.toordinal() - 1)
        return [
            (c.occasion, NewsPerson(name=c.name, date=c.date, link=c.link))
            for c in await svc.in_range(viewer, first, last_day)
            if c.occasion == "birthday" or (c.occasion == "remembrance" and memorials)
        ]

    async def _recipes(
        self, community: object, viewer: User, start: datetime, end: datetime
    ) -> list[NewsRecipe]:
        if not is_enabled(community, "recipes"):  # type: ignore[arg-type]
            return []
        return [
            NewsRecipe(id=r.id, title=r.title, author_name=n)
            for r, n in await self._repo.month_recipes(viewer.id, start, end)
        ]

    async def _capsules(
        self, community: object, viewer: User, start: datetime, end: datetime
    ) -> list[NewsCapsule]:
        if not is_enabled(community, "time_capsules"):  # type: ignore[arg-type]
            return []
        svc = TimeCapsuleService(
            TimeCapsuleRepository(self._session),
            CommunityRepository(self._session),
            NotificationService(
                NotificationRepository(self._session), SettingsRepository(self._session), self._cid
            ),
            self._cid,
        )
        return [
            NewsCapsule(id=c.id, title=c.title, author_name=c.author.display_name)
            for c in (await svc.list_for_viewer(viewer.id))["opened"]
            if c.opened_at is not None and start <= c.opened_at < end
        ]

    async def _events(
        self, viewer: User, start: datetime, end: datetime, local: ZoneInfo
    ) -> list[NewsEvent]:
        return [
            NewsEvent(
                id=e.id,
                title=e.title,
                date=e.starts_at.astimezone(local).date(),
                place=(e.location or "").strip() or None,
            )
            for e in await self._repo.month_events(viewer.id, start, end)
        ]

    async def set_override(
        self, month: str, admin: User, post_id: uuid.UUID, action: str | None
    ) -> None:
        """@brief Pin/hide/clear a post; 404 when the admin cannot open that post."""
        community = await CommunityRepository(self._session).get(self._cid)
        if community is None:
            raise NotFoundError()
        require_feature(community, "newsletter")
        parse_month(month)
        if not await self._repo.post_exists_visible(post_id, admin.id):
            raise NotFoundError()
        await self._repo.set_override(month, post_id, action, admin.id)
