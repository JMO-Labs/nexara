"""
@file link_preview_repo.py
@brief Repository for link preview cache and post/message associations.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.link_preview import ChatMessageLinkPreview, LinkPreview, PostLinkPreview
from app.repositories.base import BaseRepository

DEFAULT_EXPIRY_DAYS = 90
"""@brief Default cache expiry for link previews."""


class LinkPreviewRepository(BaseRepository[LinkPreview]):
    """
    @brief Async repository for link preview cache and associations.

    LinkPreview has no community_id; it is a global cache keyed by url_hash.
    """

    model = LinkPreview

    async def find_by_url_hash(self, url_hash: str) -> LinkPreview | None:
        """
        @brief Fetch a link preview by its URL hash.

        @param url_hash SHA256 hash of the canonical URL.
        @return The LinkPreview instance or None.
        """
        stmt = select(LinkPreview).where(LinkPreview.url_hash == url_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_or_create(
        self,
        url: str,
        url_hash: str,
        defaults: dict[str, Any],
    ) -> tuple[LinkPreview, bool]:
        """
        @brief Get existing preview by url_hash or create with defaults.

        @param url Original URL.
        @param url_hash Hash of URL for lookup.
        @param defaults Dict of fields for new row (title, description, etc.).
        @return (preview, created) where created is True if newly inserted.
        """
        existing = await self.find_by_url_hash(url_hash)
        if existing is not None:
            return (existing, False)

        expires_at = defaults.get(
            "expires_at",
            datetime.now(UTC) + timedelta(days=DEFAULT_EXPIRY_DAYS),
        )
        preview = LinkPreview(
            url=url,
            url_hash=url_hash,
            title=defaults.get("title", ""),
            description=defaults.get("description"),
            image_url=defaults.get("image_url"),
            site_name=defaults.get("site_name"),
            provider_type=defaults.get("provider_type"),
            provider_id=defaults.get("provider_id"),
            expires_at=expires_at,
            fetch_error=defaults.get("fetch_error", False),
        )
        try:
            await self.create(preview)
            return (preview, True)
        except IntegrityError:
            await self._session.rollback()
            existing = await self.find_by_url_hash(url_hash)
            if existing is not None:
                return (existing, False)
            raise

    async def create_post_link(
        self,
        post_id: uuid.UUID,
        preview_id: uuid.UUID,
        position: int,
    ) -> None:
        """
        @brief Associate a link preview with a post.

        @param post_id Post UUID.
        @param preview_id LinkPreview UUID.
        @param position Order in the post's link list.
        """
        link = PostLinkPreview(
            post_id=post_id,
            preview_id=preview_id,
            position=position,
        )
        self._session.add(link)
        await self._session.flush()

    async def create_message_link(
        self,
        message_id: uuid.UUID,
        preview_id: uuid.UUID,
        position: int,
    ) -> None:
        """
        @brief Associate a link preview with a chat message.

        @param message_id Chat message UUID.
        @param preview_id LinkPreview UUID.
        @param position Order in the message's link list.
        """
        link = ChatMessageLinkPreview(
            message_id=message_id,
            preview_id=preview_id,
            position=position,
        )
        self._session.add(link)
        await self._session.flush()

    async def get_for_post(self, post_id: uuid.UUID) -> list[LinkPreview]:
        """
        @brief Fetch link previews for a post, ordered by position.

        @param post_id Post UUID.
        @return List of LinkPreview instances.
        """
        stmt = (
            select(LinkPreview)
            .join(PostLinkPreview, PostLinkPreview.preview_id == LinkPreview.id)
            .where(PostLinkPreview.post_id == post_id)
            .order_by(PostLinkPreview.position)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
