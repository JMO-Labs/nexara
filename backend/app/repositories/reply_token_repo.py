"""
@file reply_token_repo.py
@brief Reply-by-email tokens (stored as sha256 hex only) and the reply log.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reply_token import InboundReply, ReplyToken

TOKEN_TTL = timedelta(days=30)
"""@brief How long a reply token stays valid."""


def hash_token(raw: str) -> str:
    """@return sha256 hex of a raw token."""
    return hashlib.sha256(raw.encode()).hexdigest()


class ReplyTokenRepository:
    """@brief Persistence for reply tokens and reply counts."""

    def __init__(self, session: AsyncSession) -> None:
        """@param session Async DB session."""
        self._session = session

    async def create(self, community_id: uuid.UUID, user_id: uuid.UUID, post_id: uuid.UUID) -> str:
        """
        @brief Mint a token bound to one user and one post.
        @return The raw token (only its hash is stored; never log it).
        """
        raw = secrets.token_urlsafe(18)
        self._session.add(
            ReplyToken(
                token_hash=hash_token(raw),
                community_id=community_id,
                user_id=user_id,
                post_id=post_id,
                expires_at=datetime.now(UTC) + TOKEN_TTL,
            )
        )
        await self._session.flush()
        return raw

    async def get(self, raw: str) -> ReplyToken | None:
        """@return The token row for a raw token (expiry not checked), or None."""
        return await self._session.get(ReplyToken, hash_token(raw))

    async def count_replies_since(self, user_id: uuid.UUID, since: datetime) -> int:
        """@return Email replies posted by the user since ``since``."""
        stmt = select(func.count()).where(
            InboundReply.user_id == user_id, InboundReply.created_at >= since
        )
        return int(await self._session.scalar(stmt) or 0)

    async def log_reply(self, user_id: uuid.UUID) -> None:
        """@brief Record one posted reply (rate limit)."""
        self._session.add(InboundReply(user_id=user_id))
        await self._session.flush()

    async def purge(self, now: datetime) -> None:
        """@brief Delete expired tokens and reply-log rows older than a day."""
        await self._session.execute(delete(ReplyToken).where(ReplyToken.expires_at < now))
        await self._session.execute(
            delete(InboundReply).where(InboundReply.created_at < now - timedelta(days=1))
        )
