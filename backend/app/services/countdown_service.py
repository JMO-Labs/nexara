"""
@file countdown_service.py
@brief Countdowns: scoped CRUD, follow, Home list and idempotent reminders.
"""

from __future__ import annotations

import calendar
import uuid
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.core.i18n import _
from app.models.countdown import Countdown
from app.models.post import Post
from app.models.user import User
from app.repositories.countdown_repo import CountdownRepository
from app.schemas.countdown import CountdownCreate, CountdownResponse, CountdownUpdate
from app.services.memories_service import local_today

KINDS = {7: "d7", 1: "d1", 0: "d0"}
HIDE_AFTER_DAYS = 3


def _on_year(d: date, year: int) -> date:
    """@brief Same month/day in ``year`` (Feb 29 -> Feb 28 in non-leap years)."""
    day = min(d.day, calendar.monthrange(year, d.month)[1])
    return date(year, d.month, day)


def next_occurrence(c: Countdown, today: date) -> date:
    """
    @brief The date to count down to.
    @details Yearly countdowns roll to the next year the day after the date passes.
    """
    if not c.repeat_yearly or c.target_date >= today:
        return c.target_date
    this_year = _on_year(c.target_date, today.year)
    return this_year if this_year >= today else _on_year(c.target_date, today.year + 1)


def days_left(c: Countdown, viewer_today: date) -> int:
    """@return Days from the viewer's today to the next occurrence (0 = today)."""
    return (next_occurrence(c, viewer_today) - viewer_today).days


def reminder_text(c: Countdown, left: int) -> str:
    """@brief Human message for a reminder at ``left`` days."""
    if left == 0:
        return _("Today: {title}!").format(title=c.title)
    if left == 1:
        return _("Tomorrow: {title}").format(title=c.title)
    return _("{n} days until {title}").format(n=left, title=c.title)


def _card_text(emoji: str | None, title: str) -> str:
    return f"{emoji or ''} {title}".strip()


def _valid_tz(tz: str) -> str:
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        raise ValidationError(message=_("Unknown timezone")) from None
    return tz


class CountdownService:
    """@brief Business rules for countdowns."""

    def __init__(
        self,
        repo: CountdownRepository,
        community_id: uuid.UUID,
        notifier: Any = None,
        audit: Any = None,
    ):
        self._audit = audit
        self._repo = repo
        self._cid = community_id
        self._notifier = notifier

    async def _view(self, items: list[Countdown], viewer: User) -> list[CountdownResponse]:
        today = local_today(viewer.timezone)
        counts, mine = await self._repo.follow_info([c.id for c in items], viewer.id)
        return [
            CountdownResponse(
                id=c.id,
                author_id=c.author_id,
                title=c.title,
                target_date=c.target_date,
                target_time=c.target_time,
                tz=c.tz,
                emoji=c.emoji,
                cover_media_id=c.cover_media_id,
                repeat_yearly=c.repeat_yearly,
                visibility=c.visibility,
                subgroup_id=c.subgroup_id,
                post_id=c.post_id,
                days_left=days_left(c, today),
                next_date=next_occurrence(c, today),
                following=c.id in mine,
                follower_count=counts.get(c.id, 0),
            )
            for c in items
        ]

    async def _visible(self, countdown_id: uuid.UUID, viewer: User) -> Countdown:
        c = await self._repo.get_visible(self._cid, countdown_id, viewer.id)
        if c is None:
            raise NotFoundError(_("Countdown not found"))
        return c

    async def _check_cover(self, viewer: User, media_id: uuid.UUID | None) -> None:
        if media_id is not None and not await self._repo.own_media_exists(
            self._cid, media_id, viewer.id
        ):
            raise ValidationError(message=_("Cover image not found"))

    @staticmethod
    def _check_not_past(viewer: User, target: date, yearly: bool) -> None:
        if not yearly and target < local_today(viewer.timezone):
            raise ValidationError(message=_("Date is in the past"))

    async def create(self, viewer: User, body: CountdownCreate) -> CountdownResponse:
        """@brief Create a countdown + feed post; the author follows it."""
        _valid_tz(body.tz)
        self._check_not_past(viewer, body.target_date, body.repeat_yearly)
        await self._check_cover(viewer, body.cover_media_id)
        if body.visibility == "subgroup":
            if body.subgroup_id is None or not await self._repo.is_member(
                body.subgroup_id, viewer.id
            ):
                raise AuthorizationError(message=_("You are not in that group"))
        elif body.subgroup_id is not None:
            raise ValidationError(message=_("subgroup_id requires subgroup visibility"))
        c = Countdown(
            community_id=self._cid,
            author_id=viewer.id,
            **body.model_dump(),
        )
        post = Post(
            community_id=self._cid,
            author_id=viewer.id,
            content=_card_text(body.emoji, body.title),
            visibility=body.visibility,
            subgroup_id=body.subgroup_id,
        )
        await self._repo.add(c, post)
        await self._repo.follow(c.id, viewer.id)
        return (await self._view([c], viewer))[0]

    async def get(self, viewer: User, countdown_id: uuid.UUID) -> CountdownResponse:
        """@brief One visible countdown (404 otherwise)."""
        return (await self._view([await self._visible(countdown_id, viewer)], viewer))[0]

    async def update(
        self, viewer: User, countdown_id: uuid.UUID, body: CountdownUpdate
    ) -> CountdownResponse:
        """@brief Author edits fields."""
        c = await self._visible(countdown_id, viewer)
        if c.author_id != viewer.id:
            raise AuthorizationError(message=_("Only the author can edit this countdown"))
        data = body.model_dump(exclude_unset=True)
        if data.get("title") is None:
            data.pop("title", None)
        if data.get("target_date") is None:
            data.pop("target_date", None)
        if data.get("repeat_yearly") is None:
            data.pop("repeat_yearly", None)
        if "tz" in data:
            if data["tz"] is None:
                data.pop("tz")
            else:
                _valid_tz(data["tz"])
        if "target_date" in data and data["target_date"] != c.target_date:
            self._check_not_past(
                viewer, data["target_date"], data.get("repeat_yearly", c.repeat_yearly)
            )
        await self._check_cover(viewer, data.get("cover_media_id"))
        await self._repo.apply(c, data)
        if c.post_id is not None and ("title" in data or "emoji" in data):
            await self._repo.set_post_content(c.post_id, _card_text(c.emoji, c.title))
        return (await self._view([c], viewer))[0]

    async def delete(self, viewer: User, countdown_id: uuid.UUID) -> None:
        """@brief Author or admin deletes it (and its feed post)."""
        admin = viewer.role == "admin"
        c = (
            await self._repo.get(self._cid, countdown_id)
            if admin
            else await self._visible(countdown_id, viewer)
        )
        if c is None:
            raise NotFoundError(_("Countdown not found"))
        if c.author_id != viewer.id and not admin:
            raise AuthorizationError(message=_("Only the author or an admin can delete this"))
        await self._repo.soft_delete(c)
        if admin and c.author_id != viewer.id and self._audit is not None:
            await self._audit.append(
                actor_id=viewer.id,
                action="countdown.deleted_by_admin",
                target_type="countdown",
                target_id=c.id,
                extra_data={"title": c.title, "author_id": str(c.author_id)},
            )

    async def follow(self, viewer: User, countdown_id: uuid.UUID, on: bool) -> CountdownResponse:
        """@brief Follow/unfollow (following requires visibility)."""
        c = await self._visible(countdown_id, viewer)
        if on:
            await self._repo.follow(c.id, viewer.id)
        else:
            await self._repo.unfollow(c.id, viewer.id)
        return (await self._view([c], viewer))[0]

    async def list_all(self, viewer: User) -> list[CountdownResponse]:
        """@brief Browse every visible countdown, soonest first."""
        items = await self._view(await self._repo.list_visible(self._cid, viewer.id), viewer)
        return sorted(items, key=lambda r: (r.days_left < 0, abs(r.days_left)))

    async def list_following(self, viewer: User, include_done: bool) -> list[CountdownResponse]:
        """@brief Followed countdowns soonest first, ended last; hides one-offs >3 days past."""
        items = await self._view(await self._repo.list_following(self._cid, viewer.id), viewer)
        if not include_done:
            items = [r for r in items if r.days_left >= -HIDE_AFTER_DAYS]
        return sorted(items, key=lambda r: (r.days_left < 0, abs(r.days_left)))

    async def send_reminders(self, now: datetime | None = None) -> int:
        """
        @brief Notify followers at 7 / 1 / 0 days (viewer timezone), once per occurrence.
        @return Number of notifications sent.
        """
        now = now or datetime.now(UTC)
        sent = 0
        for c, user_id, tz in await self._repo.reminder_targets(self._cid, now.date()):
            today = local_today(tz, now)
            left = days_left(c, today)
            kind = KINDS.get(left)
            if kind is None:
                continue
            if not await self._repo.mark_sent(c.id, user_id, kind, next_occurrence(c, today)):
                continue
            await self._notifier.notify(
                user_id=user_id,
                type="countdown_reminder",
                payload={"message": reminder_text(c, left), "link": f"/app/countdowns/{c.id}"},
            )
            sent += 1
        return sent
