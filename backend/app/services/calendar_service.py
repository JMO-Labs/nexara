"""
@file calendar_service.py
@brief Service layer for the Calendar entity.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import Calendar
from app.repositories.calendar_repo import CalendarRepository
from app.schemas.calendar import CalendarResponse


class CalendarService:
    """@brief List/manage user-visible calendars."""

    def __init__(
        self,
        calendar_repo: CalendarRepository,
        community_id: uuid.UUID,
        session: AsyncSession,
    ) -> None:
        self._repo = calendar_repo
        self._community_id = community_id
        self._session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[CalendarResponse]:
        """@brief Return calendars visible to ``user_id``."""
        rows = await self._repo.list_for_user(self._community_id, user_id)
        return [CalendarResponse.model_validate(r) for r in rows]

    async def derive_calendar_id(
        self,
        *,
        user_id: uuid.UUID,
        visibility: str,
        subgroup_id: uuid.UUID | None,
    ) -> uuid.UUID:
        """
        @brief Map legacy (visibility, subgroup_id, author) → calendar_id.

        Used by event creation while the ``visibility`` column remains
        authoritative. Auto-creates calendars on demand to keep the
        migration path lazy.
        """
        if visibility == "subgroup" and subgroup_id is not None:
            cal = await self._repo.get_for_subgroup(self._community_id, subgroup_id)
            if cal is None:
                # Subgroup created before calendar seeding ran.
                cal = await self._repo.ensure_for_subgroup(
                    self._community_id,
                    subgroup_id,
                    name="Subgroup",
                )
            return cal.id
        if visibility == "private":
            cal = await self._repo.ensure_personal(self._community_id, user_id)
            return cal.id
        # community (default fallback)
        cal = await self._repo.ensure_community(self._community_id)
        return cal.id

    async def get_personal(self, user_id: uuid.UUID) -> Calendar:
        """@brief Fetch (auto-create) a user's personal calendar."""
        return await self._repo.ensure_personal(self._community_id, user_id)
