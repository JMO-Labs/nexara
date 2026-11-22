"""
@file household_repo.py
@brief Household members/pets: CRUD, a "can the viewer see it" predicate
       and upcoming birthdays/gotcha days.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.household import HouseholdMember
from app.models.media import Media
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.tag import Tag
from app.repositories.visibility_preds import not_blocked


def _shares_gated_group(owner_col: Any, viewer_id: uuid.UUID) -> Any:
    """@brief Owner and viewer share a live invite-only/approval group."""
    mine, theirs = aliased(SubgroupMember), aliased(SubgroupMember)
    return (
        exists()
        .where(mine.user_id == viewer_id, theirs.user_id == owner_col)
        .where(mine.subgroup_id == theirs.subgroup_id, Subgroup.id == mine.subgroup_id)
        .where(Subgroup.archived_at.is_(None), Subgroup.join_policy != "open")
    )


def level_visible(level_col: Any, owner_col: Any, viewer_id: uuid.UUID) -> Any:
    """@brief Viewer may see something stored at ``level_col`` owned by ``owner_col``."""
    return or_(
        owner_col == viewer_id,
        level_col == "community",
        and_(level_col == "groups", _shares_gated_group(owner_col, viewer_id)),
    )


def household_visible(viewer_id: uuid.UUID, community_id: uuid.UUID) -> Any:
    """@brief Live household member the viewer may see."""
    return and_(
        HouseholdMember.community_id == community_id,
        HouseholdMember.deleted_at.is_(None),
        level_visible(HouseholdMember.visibility, HouseholdMember.owner_id, viewer_id),
        not_blocked(HouseholdMember.owner_id, viewer_id),
    )


class HouseholdRepository:
    """@brief Data access for household_members."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def visible(
        self,
        viewer_id: uuid.UUID,
        community_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
        ids: list[uuid.UUID] | None = None,
    ) -> list[HouseholdMember]:
        """@brief Members the viewer may see, optionally for one owner or ids."""
        stmt = select(HouseholdMember).where(household_visible(viewer_id, community_id))
        if owner_id is not None:
            stmt = stmt.where(HouseholdMember.owner_id == owner_id)
        if ids is not None:
            stmt = stmt.where(HouseholdMember.id.in_(ids))
        stmt = stmt.order_by(HouseholdMember.kind, HouseholdMember.name)
        return list((await self._session.execute(stmt)).scalars())

    async def get_visible(
        self, member_id: uuid.UUID, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> HouseholdMember | None:
        """@brief One member if the viewer may see it."""
        rows = await self.visible(viewer_id, community_id, ids=[member_id])
        return rows[0] if rows else None

    async def care_visible(self, member: HouseholdMember, viewer_id: uuid.UUID) -> bool:
        """@brief Viewer may read the member's care card."""
        stmt = select(
            exists().where(
                HouseholdMember.id == member.id,
                level_visible(HouseholdMember.care_visibility, HouseholdMember.owner_id, viewer_id),
            )
        )
        return bool((await self._session.execute(stmt)).scalar())

    async def create(self, **fields: Any) -> HouseholdMember:
        """@brief Insert a member."""
        row = HouseholdMember(**fields)
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update(self, member: HouseholdMember, fields: dict[str, Any]) -> HouseholdMember:
        """@brief Apply field changes."""
        for k, v in fields.items():
            setattr(member, k, v)
        await self._session.flush()
        await self._session.refresh(member)
        return member

    async def soft_delete(self, member: HouseholdMember) -> None:
        """@brief Hide the member and drop their tags."""
        member.deleted_at = datetime.now(UTC)
        await self._session.execute(
            delete(Tag).where(Tag.subject_type == "household", Tag.subject_id == member.id)
        )
        await self._session.flush()

    async def media_in_community(self, media_id: uuid.UUID, community_id: uuid.UUID) -> bool:
        """@brief Photo exists in the community."""
        stmt = select(exists().where(Media.id == media_id, Media.community_id == community_id))
        return bool((await self._session.execute(stmt)).scalar())

    async def handle_taken(self, community_id: uuid.UUID, handle: str) -> bool:
        """@brief Handle used by a live household member, a username or a group slug."""
        from app.models.subgroup import Subgroup
        from app.models.user import User

        stmt = select(
            exists().where(
                HouseholdMember.community_id == community_id,
                HouseholdMember.deleted_at.is_(None),
                HouseholdMember.handle == handle,
            )
            | exists().where(User.community_id == community_id, func.lower(User.username) == handle)
            | exists().where(func.lower(Subgroup.slug) == handle)
        )
        return bool((await self._session.execute(stmt)).scalar())
