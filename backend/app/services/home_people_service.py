"""
@file home_people_service.py
@brief HomePeopleService: ranks and privacy-filters people for the home strip.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import date

from app.models.user import User
from app.repositories.home_people_repo import HomePeopleRepository, PersonRow
from app.schemas.home_people import HomePeopleResponse, HomePerson, SharedGroup
from app.services.realtime import presence

BIRTHDAY_WINDOW_DAYS = 14


def birthday_in_days(birthday: date | None, today: date) -> int | None:
    """
    @brief Days until the next birthday if within 0..14, else None.
    @param birthday Date of birth (year ignored); Feb 29 maps to Feb 28 in non-leap years.
    @param today Reference date.
    """
    if birthday is None:
        return None
    for year in (today.year, today.year + 1):
        try:
            nxt = date(year, birthday.month, birthday.day)
        except ValueError:
            nxt = date(year, 2, 28)
        if nxt >= today:
            delta = (nxt - today).days
            return delta if delta <= BIRTHDAY_WINDOW_DAYS else None
    return None


class HomePeopleService:
    """
    @brief Builds the people strip for a viewer.

    @param repo HomePeopleRepository.
    @param community_id Community scope.
    @param online_fn Async callable returning online user id strings.
    @param today_fn Callable returning today's date.
    """

    def __init__(
        self,
        repo: HomePeopleRepository,
        community_id: uuid.UUID,
        online_fn: Callable[[], Awaitable[list[str]]] = presence.get_online_users,
        today_fn: Callable[[], date] = date.today,
    ) -> None:
        self._repo = repo
        self._community_id = community_id
        self._online_fn = online_fn
        self._today_fn = today_fn

    async def list(self, viewer: User, limit: int) -> HomePeopleResponse:
        """@brief Return up to ``limit`` people ordered online, birthday, recent."""
        rows = await self._repo.candidates(viewer.id, self._community_id, limit)
        online_ids = set(await self._online_fn())
        events = await self._repo.shared_event_counts(
            viewer.id, [r.user.id for r in rows], self._community_id
        )
        today = self._today_fn()
        people = [self._build(r, online_ids, today, events.get(r.user.id, 0)) for r in rows]
        people.sort(key=_sort_key)
        return HomePeopleResponse(items=people[:limit])

    @staticmethod
    def _build(row: PersonRow, online_ids: set[str], today: date, shared_events: int) -> HomePerson:
        u = row.user
        primary = min(row.shared_groups, key=lambda g: (g[3], g[1]), default=None)
        return HomePerson(
            user_id=u.id,
            username=u.username,
            display_name=u.display_name,
            avatar_url=u.avatar_url,
            online=row.show_online_status and str(u.id) in online_ids,
            birthday_in_days=(
                birthday_in_days(u.birthday, today) if row.show_birthday_to == "community" else None
            ),
            last_seen_at=u.last_seen_at if row.show_last_seen else None,
            shared_groups=[
                SharedGroup(id=g[0], name=g[1], accent_color=g[2]) for g in row.shared_groups
            ],
            primary_group_id=primary[0] if primary else None,
            shared_events_30d=shared_events,
        )


def _sort_key(p: HomePerson) -> tuple[bool, int, bool, float]:
    """@brief Online first, birthday soonest, then most recently seen (nulls last)."""
    bday = p.birthday_in_days if p.birthday_in_days is not None else BIRTHDAY_WINDOW_DAYS + 1
    seen = p.last_seen_at
    return (not p.online, bday, seen is None, -seen.timestamp() if seen else 0.0)
