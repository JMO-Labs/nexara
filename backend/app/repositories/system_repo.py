"""
@file system_repo.py
@brief Raw database probes for the admin System page (liveness, sizes, schema head, SMTP state).

Every call runs in a savepoint so a failed probe never poisons the caller's session.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SystemRepository:
    """@brief Instance-level DB facts; only ``smtp_state`` is tenant-scoped."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ping(self) -> None:
        """@brief ``select 1``; raises when the database is unreachable."""
        async with self._session.begin_nested():
            await self._session.execute(text("select 1"))

    async def smtp_state(self, community_id: uuid.UUID) -> tuple[datetime | None, str | None]:
        """@return ``(smtp_last_ok_at, smtp_last_error)`` for the community."""
        async with self._session.begin_nested():
            row = (
                await self._session.execute(
                    text(
                        "select smtp_last_ok_at, smtp_last_error from communities where id = :cid"
                    ),
                    {"cid": community_id},
                )
            ).first()
        return (row[0], row[1]) if row else (None, None)

    async def sizes(self, top: int = 10) -> tuple[int, list[tuple[str, int]]]:
        """@return ``(database_bytes, [(table, bytes), ...])`` for the ``top`` largest tables."""
        async with self._session.begin_nested():
            db_bytes = int(
                (
                    await self._session.execute(text("select pg_database_size(current_database())"))
                ).scalar_one()
            )
            rows = await self._session.execute(
                text(
                    "select relname, pg_total_relation_size(c.oid) from pg_class c "
                    "join pg_namespace n on n.oid = c.relnamespace "
                    "where c.relkind = 'r' and n.nspname = 'public' "
                    "order by 2 desc limit :top"
                ),
                {"top": top},
            )
            return db_bytes, [(r[0], int(r[1])) for r in rows]

    async def alembic_head(self) -> str | None:
        """@return Current ``alembic_version.version_num`` or None."""
        async with self._session.begin_nested():
            return (
                await self._session.execute(text("select version_num from alembic_version"))
            ).scalar()
