"""
@file relation_repo.py
@brief Data access for relations: pair checks, per-user lists, the
       confirmed graph and name lookups that honor blocks and household
       visibility.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import HouseholdMember
from app.models.relation import Relation
from app.models.user import User
from app.repositories.household_repo import household_visible
from app.repositories.visibility_preds import not_blocked

FAMILY_KINDS = ("parent", "child", "spouse", "partner", "sibling")


class RelationRepository:
    """@brief Async repository for Relation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **fields: Any) -> Relation | None:
        """
        @brief Insert a relation.
        @return The row, or None when the pair already exists (unique index).
        """
        rel = Relation(**fields)
        try:
            async with self._session.begin_nested():
                self._session.add(rel)
                await self._session.flush()
        except IntegrityError:
            return None
        await self._session.refresh(rel)
        return rel

    async def get(self, relation_id: uuid.UUID, community_id: uuid.UUID) -> Relation | None:
        """@brief Relation by id within the community."""
        stmt = select(Relation).where(
            Relation.id == relation_id, Relation.community_id == community_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def pair_exists(
        self,
        community_id: uuid.UUID,
        actor_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
        member_id: uuid.UUID | None = None,
    ) -> bool:
        """@brief A relation already links the actor and this person (any direction)."""
        stmt = select(Relation.id).where(Relation.community_id == community_id)
        if user_id is not None:
            stmt = stmt.where(
                or_(
                    and_(Relation.from_user_id == actor_id, Relation.to_user_id == user_id),
                    and_(Relation.from_user_id == user_id, Relation.to_user_id == actor_id),
                )
            )
        else:
            stmt = stmt.where(
                Relation.from_user_id == actor_id, Relation.to_household_member_id == member_id
            )
        return (await self._session.execute(stmt.limit(1))).first() is not None

    async def confirm(self, rel: Relation, now: datetime) -> Relation:
        """@brief Mark confirmed."""
        rel.status = "confirmed"
        rel.confirmed_at = now
        await self._session.flush()
        await self._session.refresh(rel)
        return rel

    async def delete(self, rel: Relation) -> None:
        """@brief Hard-delete a relation."""
        await self._session.delete(rel)
        await self._session.flush()

    async def involving(self, community_id: uuid.UUID, user_id: uuid.UUID) -> list[Relation]:
        """@brief Relations where the user is either side (user or household target)."""
        stmt = (
            select(Relation)
            .where(
                Relation.community_id == community_id,
                or_(Relation.from_user_id == user_id, Relation.to_user_id == user_id),
            )
            .order_by(Relation.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def pending_for(self, community_id: uuid.UUID, user_id: uuid.UUID) -> list[Relation]:
        """@brief Pending requests addressed to the user."""
        stmt = (
            select(Relation)
            .where(
                Relation.community_id == community_id,
                Relation.to_user_id == user_id,
                Relation.status == "pending",
            )
            .order_by(Relation.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def graph(self, community_id: uuid.UUID) -> list[Relation]:
        """@brief Every confirmed relation in the community."""
        stmt = select(Relation).where(
            Relation.community_id == community_id, Relation.status == "confirmed"
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def confirmed_family_between(
        self, community_id: uuid.UUID, a: uuid.UUID, b: uuid.UUID
    ) -> bool:
        """@brief A confirmed direct-family relation links users ``a`` and ``b``."""
        stmt = select(Relation.id).where(
            Relation.community_id == community_id,
            Relation.status == "confirmed",
            Relation.kind.in_(FAMILY_KINDS),
            or_(
                and_(Relation.from_user_id == a, Relation.to_user_id == b),
                and_(Relation.from_user_id == b, Relation.to_user_id == a),
            ),
        )
        return (await self._session.execute(stmt.limit(1))).first() is not None

    async def users_visible(
        self, ids: list[uuid.UUID], viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> dict[uuid.UUID, User]:
        """@brief Live users among ``ids`` the viewer is not blocked with."""
        if not ids:
            return {}
        stmt = select(User).where(
            User.id.in_(ids),
            User.community_id == community_id,
            User.deleted_at.is_(None),
            not_blocked(User.id, viewer_id),
        )
        return {u.id: u for u in (await self._session.execute(stmt)).scalars().all()}

    async def members_visible(
        self, ids: list[uuid.UUID], viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> dict[uuid.UUID, HouseholdMember]:
        """@brief Household members among ``ids`` the viewer may see."""
        if not ids:
            return {}
        stmt = select(HouseholdMember).where(
            HouseholdMember.id.in_(ids), household_visible(viewer_id, community_id)
        )
        return {m.id: m for m in (await self._session.execute(stmt)).scalars().all()}
