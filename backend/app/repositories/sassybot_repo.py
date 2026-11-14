"""
@file sassybot_repo.py
@brief Read-only queries backing the Sassybot service.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import Community
from app.models.media import Media
from app.models.post import Comment, Post, PostMedia
from app.models.user import User
from app.models.user_settings import UserSettings


class SassybotRepository:
    """@brief Queries for posts, authors, images, bot comments and community config."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_post_and_author(
        self, post_id: uuid.UUID, community_id: uuid.UUID
    ) -> tuple[Post, User, bool] | None:
        """
        @brief Fetch a live post, its author and whether the author allows Sassybot.
        @return (post, author, allowed); a missing user_settings row means allowed.
        """
        stmt = (
            select(Post, User, UserSettings.allow_sassybot)
            .join(User, User.id == Post.author_id)
            .outerjoin(UserSettings, UserSettings.user_id == User.id)
            .where(
                Post.id == post_id,
                Post.community_id == community_id,
                Post.deleted_at.is_(None),
            )
        )
        row = (await self._session.execute(stmt)).first()
        return (row[0], row[1], row[2] is not False) if row else None

    async def get_community(self, community_id: uuid.UUID) -> Community | None:
        """@brief Fetch the community (holds Sassybot settings)."""
        return await self._session.get(Community, community_id)

    @property
    def session(self) -> AsyncSession:
        """@brief The underlying session."""
        return self._session

    async def get_community_id_for_post(self, post_id: uuid.UUID) -> uuid.UUID | None:
        """@brief Community id owning a live post."""
        res = await self._session.execute(
            select(Post.community_id).where(Post.id == post_id, Post.deleted_at.is_(None))
        )
        return res.scalar_one_or_none()

    async def get_images(self, post_id: uuid.UUID) -> list[Media]:
        """@brief Image media attached to a post, in display order."""
        stmt = (
            select(Media)
            .join(PostMedia, PostMedia.media_id == Media.id)
            .where(PostMedia.post_id == post_id, Media.content_type.like("image/%"))
            .order_by(PostMedia.position)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def count_bot_comments(
        self, post_id: uuid.UUID, bot_id: uuid.UUID, community_id: uuid.UUID
    ) -> int:
        """@brief Number of comments by the bot on a post."""
        stmt = select(func.count()).where(
            Comment.post_id == post_id,
            Comment.author_id == bot_id,
            Comment.community_id == community_id,
        )
        return int((await self._session.execute(stmt)).scalar_one())
