"""
@file invite_repo.py
@brief Repository for email-based invite token management.

Invites are created by admins and stored with a SHA-256 hash of the raw
token.  Registration validates the invite by hashing the user-supplied
token and looking it up.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invite import Invite


class InviteRepository:
    """
    @brief Async repository for :class:`Invite` records.
    """

    def __init__(self, session: AsyncSession) -> None:
        """@param session Async SQLAlchemy session (injected per-request)."""
        self._session = session

    async def create(
        self,
        *,
        community_id: uuid.UUID,
        email: str,
        role: str,
        token_hash: str,
        created_by: uuid.UUID,
        expires_at: datetime,
    ) -> Invite:
        """
        @brief Persist a new invite record.

        @param community_id Community the invite belongs to.
        @param email Invitee's email address.
        @param role Role assigned on registration.
        @param token_hash SHA-256 hash of the raw invite token.
        @param created_by Admin user who created the invite.
        @param expires_at When the invite expires.
        @return The created Invite instance.
        """
        invite = Invite(
            community_id=community_id,
            email=email,
            role=role,
            token_hash=token_hash,
            created_by=created_by,
            expires_at=expires_at,
        )
        self._session.add(invite)
        await self._session.flush()
        await self._session.refresh(invite)
        return invite

    async def find_by_token_hash(self, token_hash: str) -> Invite | None:
        """
        @brief Look up an invite by its SHA-256 token hash.

        @param token_hash Hex-encoded SHA-256 digest.
        @return The matching Invite or None.
        """
        stmt = select(Invite).where(Invite.token_hash == token_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_used(self, invite_id: uuid.UUID, used_by: uuid.UUID) -> None:
        """
        @brief Mark an invite as consumed.

        @param invite_id Primary key of the invite.
        @param used_by UUID of the user who used the invite.
        """
        stmt = (
            update(Invite)
            .where(Invite.id == invite_id)
            .values(used_at=datetime.now(UTC), used_by=used_by)
        )
        await self._session.execute(stmt)

    async def list_active(
        self,
        community_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[Invite]:
        """
        @brief List active (unused, non-expired) invites for a community.

        @param community_id Community scope.
        @param limit Max items to return.
        @return List of active Invite instances.
        """
        now = datetime.now(UTC)
        stmt = (
            select(Invite)
            .where(
                Invite.community_id == community_id,
                Invite.used_at.is_(None),
                Invite.expires_at > now,
            )
            .order_by(Invite.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(
        self,
        community_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[Invite]:
        """
        @brief List all invites for a community (active, used, expired).

        @param community_id Community scope.
        @param limit Max items to return.
        @return List of Invite instances ordered by created_at desc.
        """
        stmt = (
            select(Invite)
            .where(Invite.community_id == community_id)
            .order_by(Invite.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_invite(
        self, invite_id: uuid.UUID, *, community_id: uuid.UUID | None = None
    ) -> bool:
        """
        @brief Hard-delete an invite (revoke before use).

        @param invite_id Primary key of the invite.
        @param community_id If set, only delete if invite belongs to this community.
        @return True if a row was deleted.
        """
        from sqlalchemy import delete

        stmt = delete(Invite).where(Invite.id == invite_id)
        if community_id is not None:
            stmt = stmt.where(Invite.community_id == community_id)
        result = await self._session.execute(stmt)
        return (cast(int, getattr(result, "rowcount", 0)) or 0) > 0

    def is_expired(self, invite: Invite) -> bool:
        """
        @brief Check whether an invite has expired.

        @param invite The Invite instance.
        @return True if expired.
        """
        return invite.expires_at < datetime.now(UTC)

    def is_used(self, invite: Invite) -> bool:
        """
        @brief Check whether an invite has already been redeemed.

        @param invite The Invite instance.
        @return True if used.
        """
        return invite.used_at is not None
