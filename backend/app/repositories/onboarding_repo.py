"""
@file onboarding_repo.py
@brief Repository for onboarding progress and the community's required steps.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import Community
from app.models.household import HouseholdMember
from app.models.relation import Relation
from app.models.user import User


class OnboardingRepository:
    """@brief Community-scoped onboarding reads and writes."""

    def __init__(self, session: AsyncSession) -> None:
        """@param session Async DB session."""
        self._session = session

    async def get_community(self, community_id: uuid.UUID) -> Community | None:
        """@brief The community row."""
        return await self._session.get(Community, community_id)

    async def set_required(self, community_id: uuid.UUID, required: list[str]) -> None:
        """@brief Store the steps every new member must finish."""
        await self._session.execute(
            update(Community)
            .where(Community.id == community_id)
            .values(onboarding_required=required)
        )
        await self._session.flush()

    async def set_step(self, user: User, step: int) -> None:
        """@brief Persist the wizard position."""
        user.onboarding_step = step
        await self._session.flush()

    async def mark_done(self, user: User) -> None:
        """@brief Stamp the wizard as finished."""
        user.onboarding_done_at = datetime.now(UTC)
        await self._session.flush()

    async def has_relation(self, community_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@brief Whether the user has any relation (either side, any status)."""
        stmt = (
            select(Relation.id)
            .where(
                Relation.community_id == community_id,
                or_(Relation.from_user_id == user_id, Relation.to_user_id == user_id),
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None

    async def has_family(self, community_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@brief A relation, or a household member or pet the user owns."""
        if await self.has_relation(community_id, user_id):
            return True
        stmt = (
            select(HouseholdMember.id)
            .where(
                HouseholdMember.community_id == community_id,
                HouseholdMember.owner_id == user_id,
                HouseholdMember.deleted_at.is_(None),
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None
