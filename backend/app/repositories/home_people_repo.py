"""
@file home_people_repo.py
@brief Queries backing the home people strip (candidates + shared events).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from app.models.event import Event, EventAttendance
from app.models.moderation import UserBlock
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.base import BaseRepository

SharedGroupRow = tuple[uuid.UUID, str, str | None, int]
"""@brief (subgroup id, name, accent_color, member_count)."""


@dataclass
class PersonRow:
    """@brief A candidate person with raw privacy flags and shared groups."""

    user: User
    show_online_status: bool = True
    show_last_seen: bool = True
    show_birthday_to: str = "community"
    shared_groups: list[SharedGroupRow] = field(default_factory=list)


class HomePeopleRepository(BaseRepository[User]):
    """@brief Community-scoped, block-aware people queries for the home strip."""

    model = User

    @staticmethod
    def _exclude_blocked(stmt: Any, viewer_id: uuid.UUID) -> Any:
        """@brief Exclude users blocked by, or blocking, the viewer."""
        blocked = select(UserBlock.blocked_id).where(UserBlock.blocker_id == viewer_id)
        blockers = select(UserBlock.blocker_id).where(UserBlock.blocked_id == viewer_id)
        return stmt.where(User.id.notin_(blocked), User.id.notin_(blockers))

    def _eligible(self, viewer_id: uuid.UUID, community_id: uuid.UUID) -> Any:
        """@brief Base select of eligible users plus their privacy flags."""
        stmt = (
            select(
                User,
                func.coalesce(UserSettings.show_online_status, True),
                func.coalesce(UserSettings.show_last_seen, True),
                func.coalesce(UserSettings.show_birthday_to, "community"),
            )
            .outerjoin(UserSettings, UserSettings.user_id == User.id)
            .where(
                User.community_id == community_id,
                User.id != viewer_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                User.is_bot.is_(False),
            )
        )
        return self._exclude_blocked(stmt, viewer_id)

    async def candidates(
        self, viewer_id: uuid.UUID, community_id: uuid.UUID, limit: int
    ) -> list[PersonRow]:
        """
        @brief People sharing a subgroup with the viewer, topped up with community members.
        @param viewer_id Viewing user (excluded from results).
        @param community_id Community scope.
        @param limit Desired strip size; up to ``limit * 3`` rows are returned.
        @return PersonRows, shared-group members first.
        """
        cap = limit * 3
        mine = aliased(SubgroupMember)
        theirs = aliased(SubgroupMember)
        counts = aliased(SubgroupMember)
        member_count = (
            select(func.count())
            .select_from(counts)
            .where(counts.subgroup_id == Subgroup.id)
            .scalar_subquery()
        )
        shared_stmt = (
            self._eligible(viewer_id, community_id)
            .add_columns(Subgroup.id, Subgroup.name, Subgroup.accent_color, member_count)
            .join(theirs, theirs.user_id == User.id)
            .join(mine, (mine.subgroup_id == theirs.subgroup_id) & (mine.user_id == viewer_id))
            .join(Subgroup, Subgroup.id == theirs.subgroup_id)
            .where(Subgroup.community_id == community_id, Subgroup.archived_at.is_(None))
            .order_by(User.display_name, User.id, Subgroup.name)
        )
        rows: dict[uuid.UUID, PersonRow] = {}
        for user, online, last_seen, bday, gid, gname, accent, cnt in (
            await self._session.execute(shared_stmt)
        ).all():
            row = rows.get(user.id)
            if row is None:
                if len(rows) >= cap:
                    continue
                row = rows[user.id] = PersonRow(user, online, last_seen, bday)
            row.shared_groups.append((gid, gname, accent, int(cnt)))

        if len(rows) < cap:
            fill = (
                self._eligible(viewer_id, community_id)
                .where(User.id.notin_(list(rows)) if rows else True)
                .order_by(User.last_seen_at.desc().nulls_last(), User.id)
                .limit(cap - len(rows))
            )
            for user, online, last_seen, bday in (await self._session.execute(fill)).all():
                rows[user.id] = PersonRow(user, online, last_seen, bday)
        return list(rows.values())

    async def rows_for(
        self, viewer_id: uuid.UUID, community_id: uuid.UUID, ids: list[uuid.UUID]
    ) -> list[PersonRow]:
        """
        @brief Eligible users by id (favorites missing from the candidate pool).
        @return PersonRows without shared-group detail.
        """
        if not ids:
            return []
        stmt = self._eligible(viewer_id, community_id).where(User.id.in_(ids))
        return [
            PersonRow(user, online, last_seen, bday)
            for user, online, last_seen, bday in (await self._session.execute(stmt)).all()
        ]

    async def favorites(self, viewer_id: uuid.UUID) -> list[uuid.UUID]:
        """@brief Viewer's pinned user ids from settings.home_layout.favorites."""
        layout = (
            await self._session.execute(
                select(UserSettings.home_layout).where(UserSettings.user_id == viewer_id)
            )
        ).scalar_one_or_none() or {}
        out: list[uuid.UUID] = []
        for raw in layout.get("favorites", []) if isinstance(layout, dict) else []:
            try:
                out.append(uuid.UUID(str(raw)))
            except ValueError:
                continue
        return out

    async def set_favorites(
        self, viewer_id: uuid.UUID, community_id: uuid.UUID, ids: list[uuid.UUID]
    ) -> None:
        """@brief Store pinned ids, keeping any other home_layout keys."""
        row = (
            await self._session.execute(
                select(UserSettings).where(UserSettings.user_id == viewer_id)
            )
        ).scalar_one_or_none()
        if row is None:
            row = UserSettings(user_id=viewer_id, community_id=community_id)
            self._session.add(row)
        layout = dict(row.home_layout or {})
        layout["favorites"] = [str(i) for i in ids]
        row.home_layout = layout
        await self._session.flush()

    async def shared_event_counts(
        self,
        viewer_id: uuid.UUID,
        user_ids: list[uuid.UUID],
        community_id: uuid.UUID,
        window_days: int = 30,
    ) -> dict[uuid.UUID, int]:
        """
        @brief Count events within +/- window_days that both viewer and each user attend.
        @return Map of user id to count (users with zero are omitted).
        """
        if not user_ids:
            return {}
        now = datetime.now(UTC)
        mine = aliased(EventAttendance)
        theirs = aliased(EventAttendance)
        stmt = (
            select(theirs.user_id, func.count(func.distinct(Event.id)))
            .select_from(Event)
            .join(mine, (mine.event_id == Event.id) & (mine.user_id == viewer_id))
            .join(theirs, (theirs.event_id == Event.id) & theirs.user_id.in_(user_ids))
            .where(
                Event.community_id == community_id,
                Event.starts_at >= now - timedelta(days=window_days),
                Event.starts_at <= now + timedelta(days=window_days),
                mine.status == "attending",
                theirs.status == "attending",
            )
            .group_by(theirs.user_id)
        )
        return {uid: int(n) for uid, n in (await self._session.execute(stmt)).all()}
