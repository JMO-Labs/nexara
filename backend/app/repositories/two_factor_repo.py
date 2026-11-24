"""
@file two_factor_repo.py
@brief Queries for 2FA state: recovery codes, passkey counts, community policy.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_token
from app.models.auth import UserBackupCode
from app.models.community import Community
from app.models.passkey import Passkey
from app.models.user import User


class TwoFactorRepository:
    """@brief Data access for the 2FA lifecycle (scoped by community_id)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """@brief The underlying session (for atomic helpers such as code consumption)."""
        return self._session

    async def replace_recovery_codes(self, user_id: uuid.UUID, codes: list[str]) -> None:
        """@brief Delete all of a user's recovery codes and store hashes of ``codes``."""
        await self.delete_recovery_codes(user_id)
        self._session.add_all(
            UserBackupCode(user_id=user_id, code_hash=hash_token(c)) for c in codes
        )
        await self._session.flush()

    async def delete_recovery_codes(self, user_id: uuid.UUID) -> None:
        """@brief Delete every recovery code of a user."""
        await self._session.execute(delete(UserBackupCode).where(UserBackupCode.user_id == user_id))

    async def count_recovery_left(self, user_id: uuid.UUID) -> int:
        """@brief Number of unused recovery codes."""
        stmt = select(func.count()).where(
            UserBackupCode.user_id == user_id, UserBackupCode.used_at.is_(None)
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def count_passkeys(self, user_id: uuid.UUID, community_id: uuid.UUID) -> int:
        """@brief Number of passkeys registered by a user."""
        stmt = select(func.count()).where(
            Passkey.user_id == user_id, Passkey.community_id == community_id
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def delete_passkeys(self, user_id: uuid.UUID, community_id: uuid.UUID) -> None:
        """@brief Remove every passkey of a user."""
        await self._session.execute(
            delete(Passkey).where(Passkey.user_id == user_id, Passkey.community_id == community_id)
        )

    async def get_policy(self, community_id: uuid.UUID) -> str:
        """@brief Community 2FA policy (``off`` if the community row is missing)."""
        stmt = select(Community.require_2fa).where(Community.id == community_id)
        return (await self._session.execute(stmt)).scalar_one_or_none() or "off"

    async def set_policy(self, community_id: uuid.UUID, policy: str) -> None:
        """@brief Store the policy and start (or clear) every member's grace clock."""
        await self._session.execute(
            update(Community).where(Community.id == community_id).values(require_2fa=policy)
        )
        users = update(User).where(User.community_id == community_id)
        if policy == "off":
            await self._session.execute(users.values(two_factor_required_since=None))
        else:
            await self._session.execute(
                users.where(User.two_factor_required_since.is_(None)).values(
                    two_factor_required_since=datetime.now(UTC)
                )
            )
