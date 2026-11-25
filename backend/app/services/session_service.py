"""
@file session_service.py
@brief A member's signed-in devices (refresh-token families): list and revoke.

Revocations are audited (``session.revoked`` / ``session.revoked_others``) when an
audit repository is supplied.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import AppError, NotFoundError
from app.core.i18n import _
from app.core.security import hash_token
from app.repositories.audit_repo import AuditRepository
from app.repositories.token_repo import TokenRepository
from app.schemas.signin import SessionOut
from app.services.auth.device import parse_device


class SessionService:
    """@brief Session management for one user; never touches other users' tokens."""

    def __init__(
        self,
        repo: TokenRepository,
        user_id: uuid.UUID,
        audit: AuditRepository | None = None,
        ip_address: str | None = None,
    ) -> None:
        self._repo = repo
        self._uid = user_id
        self._audit = audit
        self._ip = ip_address

    async def _record(
        self, action: str, family_id: uuid.UUID, extra: dict[str, Any] | None = None
    ) -> None:
        if self._audit is not None:
            await self._audit.append(
                actor_id=self._uid,
                action=action,
                target_type="session",
                target_id=family_id,
                extra_data=extra,
                ip_address=self._ip,
            )

    async def current_family(self, raw_refresh: str | None) -> uuid.UUID | None:
        """@return Family of the presented refresh cookie if it is this user's, else None."""
        if not raw_refresh:
            return None
        tok = await self._repo.find_by_hash(hash_token(raw_refresh))
        live = tok and tok.revoked_at is None and tok.expires_at > datetime.now(UTC)
        return tok.family_id if tok and live and tok.user_id == self._uid else None

    async def list(self, raw_refresh: str | None) -> list[SessionOut]:
        """@brief Active devices, newest first; ``current`` marks this request's family."""
        cur = await self.current_family(raw_refresh)
        return [
            SessionOut(
                family_id=t.family_id,
                device=parse_device(t.user_agent),
                ip=str(t.ip_address) if t.ip_address else None,
                last_seen=t.created_at,
                current=t.family_id == cur,
            )
            for t in await self._repo.list_active_families(self._uid)
        ]

    async def revoke(self, family_id: uuid.UUID) -> None:
        """@raises NotFoundError If the family is not an active session of this user."""
        if not await self._repo.revoke_user_family(self._uid, family_id):
            raise NotFoundError(_("Session not found"))
        await self._record("session.revoked", family_id)

    async def revoke_others(self, raw_refresh: str | None) -> int:
        """@brief Sign out every device except the current one. @return tokens revoked."""
        keep = await self.current_family(raw_refresh)
        if keep is None:
            raise AppError(
                code="NO_CURRENT_SESSION",
                message=_("Current session not found; sign in again"),
                status_code=400,
            )
        n = await self._repo.revoke_other_families(self._uid, keep)
        await self._record("session.revoked_others", keep, {"tokens": n})
        return n
