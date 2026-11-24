"""
@file passkey_repo.py
@brief Queries for WebAuthn credentials (every query scoped by community_id).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.passkey import Passkey


class PasskeyRepository:
    """@brief Data access for passkeys."""

    def __init__(self, session: AsyncSession, community_id: uuid.UUID) -> None:
        self._session, self._cid = session, community_id

    @property
    def session(self) -> AsyncSession:
        """@brief The underlying session."""
        return self._session

    async def list_for_user(self, user_id: uuid.UUID) -> list[Passkey]:
        """@brief All passkeys of a user, oldest first."""
        stmt = (
            select(Passkey)
            .where(Passkey.user_id == user_id, Passkey.community_id == self._cid)
            .order_by(Passkey.created_at)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def get_owned(self, passkey_id: uuid.UUID, user_id: uuid.UUID) -> Passkey | None:
        """@brief A passkey by id, only if it belongs to ``user_id``."""
        stmt = select(Passkey).where(
            Passkey.id == passkey_id, Passkey.user_id == user_id, Passkey.community_id == self._cid
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_credential(self, credential_id: bytes) -> Passkey | None:
        """@brief A passkey by its WebAuthn credential id."""
        stmt = select(Passkey).where(
            Passkey.credential_id == credential_id, Passkey.community_id == self._cid
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add(self, passkey: Passkey) -> Passkey:
        """@brief Persist a new passkey."""
        passkey.community_id = self._cid
        self._session.add(passkey)
        await self._session.flush()
        await self._session.refresh(passkey)
        return passkey

    async def delete(self, passkey: Passkey) -> None:
        """@brief Remove a passkey."""
        await self._session.execute(delete(Passkey).where(Passkey.id == passkey.id))

    async def touch(self, passkey: Passkey, sign_count: int) -> None:
        """@brief Record a successful use (sign counter + last_used_at)."""
        passkey.sign_count = sign_count
        passkey.last_used_at = datetime.now(UTC)
        await self._session.flush()

    async def rename(self, passkey: Passkey, name: str) -> Passkey:
        """@brief Change the display name."""
        passkey.name = name
        await self._session.flush()
        return passkey
