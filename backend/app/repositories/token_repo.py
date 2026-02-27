"""
@file token_repo.py
@brief Repository for refresh token storage with rotation and family revocation.

Refresh tokens are stored as SHA-256 hashes.  Each token belongs to a
``family_id`` — a chain of rotated tokens.  Replay of an already-rotated
token triggers revocation of the entire family (security measure).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import RefreshToken


class TokenRepository:
    """
    @brief Async repository for :class:`RefreshToken` records.

    Does not extend BaseRepository because refresh tokens have no
    ``community_id`` or soft-delete semantics.
    """

    def __init__(self, session: AsyncSession) -> None:
        """@param session Async SQLAlchemy session (injected per-request)."""
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        family_id: uuid.UUID,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> RefreshToken:
        """
        @brief Persist a new refresh token record.

        @param user_id Owner of the token.
        @param token_hash SHA-256 hash of the raw token.
        @param family_id Token rotation family identifier.
        @param expires_at Absolute expiration timestamp.
        @param ip_address Client IP at issuance.
        @param user_agent Client user-agent at issuance.
        @return The created RefreshToken instance.
        """
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._session.add(token)
        await self._session.flush()
        await self._session.refresh(token)
        return token

    async def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        """
        @brief Look up a refresh token by its SHA-256 hash.

        @param token_hash Hex-encoded SHA-256 digest.
        @return The matching RefreshToken or None.
        """
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token_id: uuid.UUID) -> None:
        """
        @brief Revoke a single refresh token by setting ``revoked_at``.

        @param token_id Primary key of the token to revoke.
        """
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)

    async def revoke_family(self, family_id: uuid.UUID) -> int:
        """
        @brief Revoke all tokens in a rotation family.

        Used when a replayed (already-rotated) token is detected — indicates
        a potential token theft, so the entire chain is invalidated.

        @param family_id The family to revoke.
        @return Number of tokens revoked.
        """
        now = datetime.now(UTC)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        """
        @brief Revoke every active refresh token for a user (e.g. password change).

        @param user_id The user whose tokens should be revoked.
        @return Number of tokens revoked.
        """
        now = datetime.now(UTC)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def cleanup_expired(self) -> int:
        """
        @brief Delete tokens that are both expired and revoked.

        Intended to be called by a periodic Celery task.

        @return Number of rows deleted.
        """
        from sqlalchemy import delete

        now = datetime.now(UTC)
        stmt = delete(RefreshToken).where(RefreshToken.expires_at < now)
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]
