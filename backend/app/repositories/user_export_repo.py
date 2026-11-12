"""
@file user_export_repo.py
@brief Data access for user data exports.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.core.exceptions import NotFoundError
from app.models.user_export import UserExport
from app.repositories.base import BaseRepository


class UserExportRepository(BaseRepository[UserExport]):
    """@brief Repository for UserExport rows (hard rows; no soft delete)."""

    model = UserExport

    async def create(  # type: ignore[override]
        self, user_id: uuid.UUID, community_id: uuid.UUID
    ) -> UserExport:
        """@brief Insert a pending export. @return The created UserExport."""
        return await super().create(
            UserExport(user_id=user_id, community_id=community_id, status="pending")
        )

    async def get_latest_by_user(
        self, user_id: uuid.UUID, community_id: uuid.UUID | None = None
    ) -> UserExport | None:
        """@brief Most recent export for a user. @return UserExport or None."""
        stmt = select(UserExport).where(UserExport.user_id == user_id)
        if community_id is not None:
            stmt = stmt.where(UserExport.community_id == community_id)
        stmt = stmt.order_by(UserExport.created_at.desc()).limit(1)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def update_status(self, export_id: uuid.UUID, status: str, **fields: Any) -> UserExport:
        """
        @brief Set status plus optional columns (file_key, ready_at, expires_at, ...).
        @param export_id Export primary key.
        @param status New status.
        @param fields Extra column values to set.
        @return The updated UserExport.
        """
        export = await self.get_by_id(export_id)
        if export is None:
            raise NotFoundError("Export not found")
        export.status = status
        for name, value in fields.items():
            setattr(export, name, value)
        await self._session.flush()
        await self._session.refresh(export)
        return export
