"""
@file admin_signin_service.py
@brief Admin view of the sign-in log: filtered pages and a capped, injection-safe CSV stream.
"""

from __future__ import annotations

import csv
import io
import uuid
from collections.abc import AsyncIterator, Callable
from datetime import datetime
from typing import Any

from app.core.exceptions import AppError
from app.core.i18n import _
from app.models.signin_event import SIGNIN_METHODS
from app.repositories.signin_repo import Row, SigninRepository
from app.schemas.signin import SigninPage, SigninRow

CSV_HEADER = ("time", "email", "user", "method", "success", "reason", "ip", "device")
CSV_MAX_ROWS = 50_000
_BATCH = 1000
_DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value: object) -> str:
    """@brief Stringify a cell and prefix a single quote when a spreadsheet would run it."""
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_DANGEROUS) else text


def _row(ev: Any, username: str | None) -> SigninRow:
    return SigninRow(
        id=ev.id,
        time=ev.created_at,
        email=ev.email_tried,
        user=username,
        method=ev.method,
        success=ev.success,
        reason=ev.reason,
        ip=str(ev.ip) if ev.ip else None,
        device=ev.device,
    )


def _encode_cursor(ev: Any) -> str:
    return f"{ev.created_at.isoformat()}|{ev.id}"


def _decode_cursor(cursor: str | None) -> tuple[datetime, uuid.UUID] | None:
    if not cursor:
        return None
    try:
        ts, eid = cursor.split("|", 1)
        return datetime.fromisoformat(ts), uuid.UUID(eid)
    except ValueError as exc:
        raise AppError(code="INVALID_CURSOR", message=_("Invalid cursor"), status_code=400) from exc


class AdminSigninService:
    """@brief Community-scoped sign-in log for admins; exports are audited."""

    def __init__(
        self,
        repo: SigninRepository,
        community_id: uuid.UUID,
        audit_repo: Any,
        actor_id: uuid.UUID,
        ip_address: str | None,
        commit: Callable[[], Any],
        reader: Callable[[], Any],
    ) -> None:
        self._repo = repo
        self._cid = community_id
        self._audit = audit_repo
        self._actor = actor_id
        self._ip = ip_address
        self._commit = commit
        self._reader = reader

    @staticmethod
    def _check_method(method: str | None) -> None:
        if method and method not in SIGNIN_METHODS:
            raise AppError(code="INVALID_METHOD", message=_("Unknown method"), status_code=400)

    async def list(
        self,
        *,
        q: str | None,
        success: bool | None,
        method: str | None,
        since: datetime | None,
        cursor: str | None,
        limit: int = 50,
    ) -> SigninPage:
        """@brief One newest-first page plus the cursor of the next."""
        self._check_method(method)
        rows = await self._repo.search(
            self._cid,
            q=q,
            success=success,
            method=method,
            since=since,
            after=_decode_cursor(cursor),
            limit=limit + 1,
        )
        more = len(rows) > limit
        rows = rows[:limit]
        return SigninPage(
            items=[_row(e, u) for e, u in rows],
            next_cursor=_encode_cursor(rows[-1][0]) if more else None,
        )

    async def export_csv(
        self,
        *,
        q: str | None,
        success: bool | None,
        method: str | None,
        since: datetime | None,
    ) -> AsyncIterator[str]:
        """
        @brief Audit the export, then stream up to 50 000 matching rows as CSV text.

        Rows are read in keyset batches through a dedicated read session, so
        memory stays flat and the request session's lifetime does not matter.
        """
        self._check_method(method)
        await self._audit.append(
            actor_id=self._actor,
            action="signins.exported",
            target_type="signin_log",
            extra_data={"q": q, "success": success, "method": method},
            ip_address=self._ip,
        )
        await self._commit()
        return self._stream(q, success, method, since)

    async def _stream(
        self, q: str | None, success: bool | None, method: str | None, since: datetime | None
    ) -> AsyncIterator[str]:
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
        after: tuple[datetime, uuid.UUID] | None = None
        async with self._reader() as session:
            repo = SigninRepository(session)
            while sent < CSV_MAX_ROWS:
                rows: list[Row] = await repo.search(
                    self._cid,
                    q=q,
                    success=success,
                    method=method,
                    since=since,
                    after=after,
                    limit=min(_BATCH, CSV_MAX_ROWS - sent),
                )
                for ev, username in rows:
                    r = _row(ev, username)
                    yield flush(
                        tuple(
                            csv_safe(c)
                            for c in (
                                r.time.isoformat(),
                                r.email,
                                r.user,
                                r.method,
                                "true" if r.success else "false",
                                r.reason,
                                r.ip,
                                r.device,
                            )
                        )
                    )
                sent += len(rows)
                if len(rows) < _BATCH:
                    break
                after = (rows[-1][0].created_at, rows[-1][0].id)
