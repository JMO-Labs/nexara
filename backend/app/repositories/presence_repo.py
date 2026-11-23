"""
@file presence_repo.py
@brief Privacy-aware lookup of which users a viewer may see presence for.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, or_, select

from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.base import BaseRepository
from app.repositories.visibility_preds import not_blocked


@dataclass
class PresenceRow:
    """@brief A visible user with raw privacy flags."""

    user_id: uuid.UUID
    show_online_status: bool
    show_last_seen: bool
    last_seen_at: datetime | None


class PresenceRepository(BaseRepository[User]):
    """@brief Community-scoped, block-aware presence candidates."""

    model = User

    async def visible(
        self, viewer_id: uuid.UUID, community_id: uuid.UUID, ids: list[uuid.UUID]
    ) -> list[PresenceRow]:
        """
        @brief Active, non-memorialized, unblocked same-community users among ids.
        @param viewer_id Viewing user (always included when in ids).
        @param community_id Community scope.
        @param ids Requested user ids.
        @return Rows with raw privacy flags (defaults true when no settings row).
        """
        if not ids:
            return []
        stmt = (
            select(
                User.id,
                func.coalesce(UserSettings.show_online_status, True),
                func.coalesce(UserSettings.show_last_seen, True),
                User.last_seen_at,
            )
            .outerjoin(UserSettings, UserSettings.user_id == User.id)
            .where(
                User.id.in_(ids),
                User.community_id == community_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                User.memorialized_at.is_(None),
                or_(User.id == viewer_id, not_blocked(User.id, viewer_id)),
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return [PresenceRow(r[0], bool(r[1]), bool(r[2]), r[3]) for r in rows]
