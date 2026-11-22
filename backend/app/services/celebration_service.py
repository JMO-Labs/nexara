"""
@file celebration_service.py
@brief Calendar view of birthdays and gotcha days in a date range, for
       members (shared with the community, or your own) and household
       members/pets the viewer may see.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from app.core.exceptions import ValidationError
from app.core.i18n import _
from app.models.user import User
from app.repositories.celebration_repo import CelebrationRepository
from app.repositories.household_repo import HouseholdRepository
from app.schemas.celebration import CalendarCelebration

MAX_RANGE_DAYS = 400


def occurrences(day: date, start: date, end: date) -> list[date]:
    """
    @brief Anniversaries of ``day`` within [start, end] (inclusive).
    @details Feb 29 falls on Feb 28 in non-leap years.
    """
    out: list[date] = []
    for year in range(start.year, end.year + 1):
        try:
            d = date(year, day.month, day.day)
        except ValueError:
            d = date(year, 2, 28)
        if start <= d <= end:
            out.append(d)
    return out


class CelebrationService:
    """@brief Builds calendar celebrations for one viewer."""

    def __init__(
        self,
        repo: CelebrationRepository,
        household: HouseholdRepository,
        community_id: uuid.UUID,
    ) -> None:
        self._repo = repo
        self._household = household
        self._cid = community_id

    async def in_range(self, viewer: User, start: date, end: date) -> list[CalendarCelebration]:
        """@brief Celebrations from start to end, sorted by date then name."""
        if end < start or (end - start) > timedelta(days=MAX_RANGE_DAYS):
            raise ValidationError(message=_("Pick a range of up to 400 days"))
        out: list[CalendarCelebration] = []
        for uid, username, name, bday in await self._repo.user_birthdays(self._cid, viewer.id):
            out += [
                CalendarCelebration(
                    date=d,
                    occasion="birthday",
                    subject_type="user",
                    subject_id=uid,
                    name=name,
                    link=f"/app/u/{username}",
                )
                for d in occurrences(bday, start, end)
            ]
        for m in await self._household.visible(viewer.id, self._cid):
            pet = m.kind == "pet"
            for occasion, day in (("birthday", m.birthday), ("gotcha_day", m.gotcha_day)):
                if day is None or (occasion == "gotcha_day" and not pet):
                    continue
                out += [
                    CalendarCelebration(
                        date=d,
                        occasion=occasion,
                        subject_type="household",
                        subject_id=m.id,
                        name=m.name,
                        is_pet=pet,
                        link=f"/app/household/{m.id}",
                    )
                    for d in occurrences(day, start, end)
                ]
        return sorted(out, key=lambda c: (c.date, c.name.lower()))
