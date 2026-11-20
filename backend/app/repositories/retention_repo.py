"""
@file retention_repo.py
@brief Queries for the instance-wide ``retention_policies`` table.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.retention import RetentionPolicy


class RetentionRepository:
    """@brief Retention policy persistence (table has no community_id)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[RetentionPolicy]:
        """@brief All stored policy rows ordered by key."""
        res = await self._session.execute(
            select(RetentionPolicy).order_by(RetentionPolicy.policy_key)
        )
        return list(res.scalars().all())

    async def upsert(
        self,
        key: str,
        enabled: bool,
        retention_days: int | None,
        delete_media_files: bool,
        user_id: uuid.UUID | None,
    ) -> RetentionPolicy:
        """
        @brief Insert or update one policy row.
        @param key policy_key
        @param enabled Whether the policy runs
        @param retention_days Days to keep, None = forever
        @param delete_media_files Also delete media files
        @param user_id Admin performing the change
        @return The persisted row
        """
        values = {
            "policy_key": key,
            "enabled": enabled,
            "retention_days": retention_days,
            "delete_media_files": delete_media_files,
            "updated_by": user_id,
        }
        stmt = (
            insert(RetentionPolicy)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[RetentionPolicy.policy_key],
                set_={
                    **{k: v for k, v in values.items() if k != "policy_key"},
                    "updated_at": func.now(),
                },
            )
            .returning(RetentionPolicy)
            .execution_options(populate_existing=True)
        )
        res = await self._session.execute(stmt)
        return res.scalar_one()
