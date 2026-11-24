"""
@file admin_audit_service.py
@brief Admin audit log: filtered, name-enriched pages and a capped, injection-safe CSV stream.
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.schemas.admin import AuditLogEntry
from app.schemas.common import PaginatedResponse
from app.services.admin_signin_service import csv_safe

CSV_HEADER = ("time", "actor", "action", "target_type", "target_id", "ip", "details")
CSV_MAX_ROWS = 50_000
_BATCH = 1000


async def _enrich(db: AsyncSession, rows: list[Any]) -> list[AuditLogEntry]:
    """@brief Attach actor and (user) target display names to rows."""
    ids = {r.actor_id for r in rows if r.actor_id}
    ids |= {r.target_id for r in rows if r.target_id and r.target_type == "user"}
    names: dict[uuid.UUID, str] = {}
    if ids:
        res = await db.execute(select(User.id, User.display_name).where(User.id.in_(ids)))
        names = {r.id: r.display_name for r in res}
    items: list[AuditLogEntry] = []
    for e in rows:
        item = AuditLogEntry.model_validate(e)
        item.actor_display_name = names.get(e.actor_id) if e.actor_id else None
        if e.target_id and e.target_type == "user":
            item.target_display = names.get(e.target_id)
        items.append(item)
    return items


class AdminAuditService:
    """@brief Read-only audit views for admins; CSV exports are themselves audited."""

    def __init__(
        self,
        db: AsyncSession,
        actor_id: uuid.UUID,
        ip_address: str | None,
        reader: Callable[[], Any],
    ) -> None:
        self._db = db
        self._repo = AuditRepository(db)
        self._actor = actor_id
        self._ip = ip_address
        self._reader = reader

    async def list(
        self, *, limit: int, cursor: str | None, **filters: Any
    ) -> PaginatedResponse[AuditLogEntry]:
        """@brief One newest-first page; ``filters`` as for ``list_entries``."""
        rows, nxt = await self._repo.list_entries(limit=limit, cursor=cursor, **filters)
        return PaginatedResponse(
            items=await _enrich(self._db, rows), next_cursor=nxt, has_more=nxt is not None
        )

    async def export_csv(self, **filters: Any) -> AsyncIterator[str]:
        """
        @brief Audit the export, then stream up to 50 000 matching rows as CSV text.

        Rows are read in keyset batches through a dedicated read session.
        """
        await self._repo.append(
            actor_id=self._actor,
            action="audit.exported",
            target_type="audit_log",
            extra_data={k: None if v is None else str(v) for k, v in filters.items()},
            ip_address=self._ip,
        )
        await self._db.commit()
        return self._stream(filters)

    async def _stream(self, filters: dict[str, Any]) -> AsyncIterator[str]:
        buf = io.StringIO()
        writer = csv.writer(buf)

        def flush(cells: tuple[object, ...]) -> str:
            writer.writerow(cells)
            out = buf.getvalue()
            buf.seek(0)
            buf.truncate()
            return out

        yield flush(CSV_HEADER)
        sent = 0
        cursor: str | None = None
        async with self._reader() as session:
            repo = AuditRepository(session)
            while sent < CSV_MAX_ROWS:
                rows, cursor = await repo.list_entries(
                    limit=min(_BATCH, CSV_MAX_ROWS - sent), cursor=cursor, **filters
                )
                for r in await _enrich(session, rows):
                    detail = json.dumps(r.extra_data, sort_keys=True) if r.extra_data else ""
                    yield flush(
                        tuple(
                            csv_safe(c)
                            for c in (
                                r.created_at.isoformat(),
                                r.actor_display_name or "",
                                r.action,
                                r.target_type,
                                r.target_id,
                                r.ip_address,
                                detail,
                            )
                        )
                    )
                sent += len(rows)
                if cursor is None:
                    break
