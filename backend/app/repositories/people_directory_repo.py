"""
@file people_directory_repo.py
@brief Paged, searchable people directory queries (extends the home people repo).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy.orm import aliased

from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.home_people_repo import HomePeopleRepository, PersonRow


def _like_escape(text: str) -> str:
    """@brief Escape LIKE wildcards so user input matches literally."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class PeopleDirectoryRepository(HomePeopleRepository):
    """@brief Community-scoped, block- and privacy-aware directory listing."""

    async def page(
        self,
        viewer_id: uuid.UUID,
        community_id: uuid.UUID,
        *,
        viewer_is_admin: bool,
        q: str | None,
        online_ids: list[str] | None,
        groups_only: bool,
        offset: int,
        limit: int,
    ) -> list[PersonRow]:
        """
        @brief One page of eligible people ordered by display name.
        @param viewer_id Viewing user (excluded).
        @param community_id Community scope.
        @param viewer_is_admin Admins may see ``admin_only`` profiles.
        @param q Case-insensitive substring of display name or username.
        @param online_ids When not None, restrict to these ids (respecting show_online_status).
        @param groups_only Restrict to people sharing a subgroup with the viewer.
        @param offset Rows to skip.
        @param limit Max rows.
        @return PersonRows with shared groups attached.
        """
        stmt = self._eligible(viewer_id, community_id)
        if not viewer_is_admin:
            visible = func.coalesce(UserSettings.profile_visible_to, "community")
            stmt = stmt.where(visible != "admin_only")
        if q:
            pat = f"%{_like_escape(q.strip())}%"
            stmt = stmt.where(
                User.display_name.ilike(pat, escape="\\") | User.username.ilike(pat, escape="\\")
            )
        if online_ids is not None:
            uids = [uuid.UUID(i) for i in online_ids]
            stmt = stmt.where(
                User.id.in_(uids), func.coalesce(UserSettings.show_online_status, True).is_(True)
            )
        if groups_only:
            stmt = stmt.where(self._shares_group(viewer_id, community_id))
        stmt = stmt.order_by(User.display_name, User.id).offset(offset).limit(limit)
        rows = [
            PersonRow(u, online, last_seen, bday)
            for u, online, last_seen, bday in (await self._session.execute(stmt)).all()
        ]
        await self._attach_groups(rows, viewer_id, community_id)
        return rows

    @staticmethod
    def _shares_group(viewer_id: uuid.UUID, community_id: uuid.UUID) -> Any:
        """@brief EXISTS clause: user shares an active subgroup with the viewer."""
        mine = aliased(SubgroupMember)
        theirs = aliased(SubgroupMember)
        return exists(
            select(1)
            .select_from(theirs)
            .join(mine, (mine.subgroup_id == theirs.subgroup_id) & (mine.user_id == viewer_id))
            .join(Subgroup, Subgroup.id == theirs.subgroup_id)
            .where(
                theirs.user_id == User.id,
                Subgroup.community_id == community_id,
                Subgroup.archived_at.is_(None),
            )
        )

    async def _attach_groups(
        self, rows: list[PersonRow], viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> None:
        """@brief Fill ``shared_groups`` on each row (one query for the whole page)."""
        if not rows:
            return
        mine = aliased(SubgroupMember)
        theirs = aliased(SubgroupMember)
        counts = aliased(SubgroupMember)
        member_count = (
            select(func.count())
            .select_from(counts)
            .where(counts.subgroup_id == Subgroup.id)
            .scalar_subquery()
        )
        stmt = (
            select(theirs.user_id, Subgroup.id, Subgroup.name, Subgroup.accent_color, member_count)
            .join(mine, (mine.subgroup_id == theirs.subgroup_id) & (mine.user_id == viewer_id))
            .join(Subgroup, Subgroup.id == theirs.subgroup_id)
            .where(
                theirs.user_id.in_([r.user.id for r in rows]),
                Subgroup.community_id == community_id,
                Subgroup.archived_at.is_(None),
            )
            .order_by(Subgroup.name)
        )
        by_user = {r.user.id: r for r in rows}
        for uid, gid, name, accent, cnt in (await self._session.execute(stmt)).all():
            by_user[uid].shared_groups.append((gid, name, accent, int(cnt)))
