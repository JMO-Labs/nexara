"""
@file age_repo.py
@brief Repository for age suggestions, community age settings and user group writes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.age_suggestion import AgeSuggestion
from app.models.community import Community
from app.models.user import User


class AgeRepository:
    """@brief Community-scoped access to age suggestions and age settings."""

    def __init__(self, session: AsyncSession) -> None:
        """@param session Async DB session."""
        self._session = session

    async def get_community(self, community_id: uuid.UUID) -> Community | None:
        """@brief The community row."""
        return await self._session.get(Community, community_id)

    async def set_adult_requires_approval(self, community_id: uuid.UUID, value: bool) -> None:
        """@brief Toggle approval mode for birthday-derived adults."""
        await self._session.execute(
            update(Community)
            .where(Community.id == community_id)
            .values(adult_requires_approval=value)
        )
        await self._session.flush()

    async def get_user(self, community_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
        """@brief Active user of this community."""
        res = await self._session.execute(
            select(User).where(
                User.id == user_id,
                User.community_id == community_id,
                User.deleted_at.is_(None),
            )
        )
        return res.scalar_one_or_none()

    async def set_user_group(self, user: User, group: str | None) -> None:
        """@brief Persist the admin-set age group (None clears)."""
        user.age_group = group
        await self._session.flush()

    async def list_admin_ids(self, community_id: uuid.UUID) -> list[uuid.UUID]:
        """@brief Active admin user ids."""
        res = await self._session.execute(
            select(User.id).where(
                User.community_id == community_id,
                User.role == "admin",
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
        )
        return list(res.scalars())

    async def pending_exists(
        self, community_id: uuid.UUID, subject_id: uuid.UUID, suggested_by: uuid.UUID
    ) -> bool:
        """@brief Whether this member already has a pending suggestion for the subject."""
        res = await self._session.execute(
            select(AgeSuggestion.id).where(
                AgeSuggestion.community_id == community_id,
                AgeSuggestion.subject_id == subject_id,
                AgeSuggestion.suggested_by == suggested_by,
                AgeSuggestion.status == "pending",
            )
        )
        return res.first() is not None

    async def create(
        self,
        community_id: uuid.UUID,
        subject_id: uuid.UUID,
        suggested_by: uuid.UUID,
        age_group: str,
        note: str | None,
    ) -> AgeSuggestion:
        """@brief Insert a pending suggestion."""
        row = AgeSuggestion(
            community_id=community_id,
            subject_id=subject_id,
            suggested_by=suggested_by,
            age_group=age_group,
            note=note,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get(self, community_id: uuid.UUID, suggestion_id: uuid.UUID) -> AgeSuggestion | None:
        """@brief One suggestion in this community."""
        res = await self._session.execute(
            select(AgeSuggestion).where(
                AgeSuggestion.id == suggestion_id, AgeSuggestion.community_id == community_id
            )
        )
        return res.scalar_one_or_none()

    async def list(self, community_id: uuid.UUID, status: str | None) -> list[AgeSuggestion]:
        """@brief Suggestions, newest first, optionally by status."""
        stmt = select(AgeSuggestion).where(AgeSuggestion.community_id == community_id)
        if status:
            stmt = stmt.where(AgeSuggestion.status == status)
        res = await self._session.execute(stmt.order_by(AgeSuggestion.created_at.desc()))
        return list(res.scalars())

    async def decide(self, row: AgeSuggestion, status: str, decided_by: uuid.UUID) -> None:
        """@brief Mark a suggestion approved/rejected."""
        row.status = status
        row.decided_by = decided_by
        row.decided_at = datetime.now(UTC)
        await self._session.flush()
