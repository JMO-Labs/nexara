"""
@file recap_service.py
@brief Family recap email: due-date logic, section assembly and the
       idempotent hourly dispatch.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.features import is_enabled
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.recap_repo import RecapRepository
from app.services.memories_service import local_today
from app.services.notifications.dnd import effective_tz
from app.services.recap_sections import SECTIONS, RecapContext, RecapSection

SEND_HOUR = 8
"""@brief Local hour at which the recap goes out."""

UNSUBSCRIBE_TTL = timedelta(days=90)
"""@brief Lifetime of the unsubscribe link."""


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return ZoneInfo("UTC")


def recap_due(cadence: str, local_now: datetime, last_sent: datetime | None) -> bool:
    """
    @param cadence ``weekly`` | ``monthly`` | ``off``.
    @param local_now Aware time in the user's zone.
    @param last_sent When the last recap was stamped, or None.
    @return True when this hour is the user's send slot and none went out recently.
    """
    if local_now.hour != SEND_HOUR:
        return False
    if cadence == "weekly":
        return local_now.weekday() == 6 and (
            last_sent is None or local_now - last_sent >= timedelta(days=6)
        )
    if cadence == "monthly":
        return local_now.day == 1 and (
            last_sent is None or local_now - last_sent >= timedelta(days=27)
        )
    return False


class RecapService:
    """@brief Builds and schedules recap emails for one community."""

    def __init__(self, session: AsyncSession, community_id: uuid.UUID) -> None:
        self._session = session
        self._cid = community_id
        self._repo = RecapRepository(session)

    async def build(self, user: User, now: datetime | None = None) -> list[RecapSection]:
        """
        @param user Recipient.
        @param now Test hook; defaults to the current time.
        @return Non-empty sections, in order; ``[]`` when there is nothing to say.
        """
        community = await CommunityRepository(self._session).get(self._cid)
        if community is None:
            raise NotFoundError()
        if not is_enabled(community, "recap"):
            return []
        now = now or datetime.now(UTC)
        ctx = RecapContext(
            user, community, self._session, now, local_today(user.timezone, now), user.timezone
        )
        out: list[RecapSection] = []
        for builder in SECTIONS:
            section = await builder(ctx)
            if section is not None and section["items"]:
                out.append(section)
        return out

    async def due_user_ids(self, now: datetime) -> list[uuid.UUID]:
        """
        @brief Find users due now and stamp ``recap_last_sent_at`` for each, so a
               second run in the same hour finds nobody.
        @param now Aware current time.
        @return Ids to enqueue (empty when the recap flag is off).
        """
        community = await CommunityRepository(self._session).get(self._cid)
        if community is None or not is_enabled(community, "recap"):
            return []
        due: list[uuid.UUID] = []
        for c in await self._repo.candidates(self._cid):
            local = now.astimezone(_zone(effective_tz(c.timezone, c.dnd_timezone)))
            if recap_due(c.cadence, local, c.last_sent_at):
                await self._repo.stamp_sent(c.user_id, now)
                due.append(c.user_id)
        return due
