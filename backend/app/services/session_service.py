"""
@file session_service.py
@brief A member's signed-in devices (refresh-token families): list and revoke.
"""

from __future__ import annotations

import uuid

from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.core.security import hash_token
from app.repositories.token_repo import TokenRepository
from app.schemas.signin import SessionOut
from app.services.auth.device import parse_device


class SessionService:
    """@brief Session management for one user; never touches other users' tokens."""

    def __init__(self, repo: TokenRepository, user_id: uuid.UUID) -> None:
        self._repo = repo
        self._uid = user_id

    async def current_family(self, raw_refresh: str | None) -> uuid.UUID | None:
        """@return Family of the presented refresh cookie if it is this user's, else None."""
        if not raw_refresh:
            return None
        tok = await self._repo.find_by_hash(hash_token(raw_refresh))
        return tok.family_id if tok and tok.user_id == self._uid else None

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

    async def revoke_others(self, raw_refresh: str | None) -> int:
        """@brief Sign out every device except the current one. @return tokens revoked."""
        return await self._repo.revoke_other_families(
            self._uid, await self.current_family(raw_refresh)
        )
