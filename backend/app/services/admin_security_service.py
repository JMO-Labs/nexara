"""
@file admin_security_service.py
@brief Admin 2FA tools: reset a member's 2FA and set the community policy.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.repositories.two_factor_repo import TwoFactorRepository
from app.repositories.user_repo import UserRepository

POLICIES = ("off", "admins", "everyone")


class AdminSecurityService:
    """@brief Community-scoped admin security actions with audit logging."""

    def __init__(
        self,
        users: UserRepository,
        repo: TwoFactorRepository,
        audit: Any,
        community_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip: str | None = None,
    ) -> None:
        self._users, self._repo, self._audit = users, repo, audit
        self._cid, self._actor, self._ip = community_id, actor_id, ip

    async def reset_2fa(self, user_id: uuid.UUID) -> None:
        """@brief Clear TOTP, recovery codes and passkeys of one member."""
        user = await self._users.get_by_id(user_id, self._cid)
        if user is None:
            raise NotFoundError(_("User not found"))
        await self._users.update_totp(
            user_id, totp_secret=None, totp_pending_secret=None, totp_enabled=False
        )
        await self._repo.delete_recovery_codes(user_id)
        await self._repo.delete_passkeys(user_id, self._cid)
        await self._audit.append(
            actor_id=self._actor,
            action="admin.user.2fa_reset",
            target_type="user",
            target_id=user_id,
            ip_address=self._ip,
        )

    async def get_policy(self) -> str:
        """@brief Current ``require_2fa`` value."""
        return await self._repo.get_policy(self._cid)

    async def set_policy(self, policy: str) -> str:
        """@brief Store ``require_2fa`` (off | admins | everyone)."""
        await self._repo.set_policy(self._cid, policy)
        await self._audit.append(
            actor_id=self._actor,
            action="admin.security.updated",
            target_type="community",
            target_id=self._cid,
            extra_data={"require_2fa": policy},
            ip_address=self._ip,
        )
        return policy
