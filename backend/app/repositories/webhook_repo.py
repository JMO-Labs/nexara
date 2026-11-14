"""
@file webhook_repo.py
@brief Repository for webhook subscriptions (user- and community-level).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import any_, func, literal, or_, select

from app.models.webhook import WebhookSubscription
from app.repositories.base import BaseRepository

MAX_FAILURES = 10
"""@brief Consecutive failures after which a subscription is auto-disabled."""


class WebhookRepository(BaseRepository[WebhookSubscription]):
    """@brief Async repository for :class:`WebhookSubscription`."""

    model = WebhookSubscription

    # create() takes extra domain args, narrower than base
    async def create(  # type: ignore[override]
        self,
        community_id: uuid.UUID,
        user_id: uuid.UUID | None,
        url: str,
        secret: str,
        type_keys: list[str],
    ) -> WebhookSubscription:
        """
        @brief Insert a subscription.
        @param community_id Owning community.
        @param user_id Owner, or None for a community-level subscription.
        @param url Target URL.
        @param secret HMAC signing secret.
        @param type_keys Notification types to deliver (empty = all).
        @return The persisted row.
        """
        sub = WebhookSubscription(
            community_id=community_id,
            user_id=user_id,
            url=url,
            secret=secret,
            type_keys=type_keys,
        )
        self._session.add(sub)
        await self._session.flush()
        await self._session.refresh(sub)
        return sub

    async def get(self, sub_id: uuid.UUID) -> WebhookSubscription | None:
        """@brief Fetch a subscription by id (None when missing)."""
        result = await self._session.execute(
            select(WebhookSubscription).where(WebhookSubscription.id == sub_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[WebhookSubscription]:
        """@brief All user-level subscriptions of a user, oldest first."""
        stmt = (
            select(WebhookSubscription)
            .where(WebhookSubscription.user_id == user_id)
            .order_by(WebhookSubscription.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_for_community(self, community_id: uuid.UUID) -> list[WebhookSubscription]:
        """@brief All community-level subscriptions (``user_id IS NULL``)."""
        stmt = (
            select(WebhookSubscription)
            .where(
                WebhookSubscription.community_id == community_id,
                WebhookSubscription.user_id.is_(None),
            )
            .order_by(WebhookSubscription.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_matching(
        self, community_id: uuid.UUID, user_id: uuid.UUID, type_key: str
    ) -> list[WebhookSubscription]:
        """
        @brief Enabled subscriptions for a delivery: user-level OR community-level,
        whose ``type_keys`` is empty (all types) or contains ``type_key``.
        """
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.community_id == community_id,
            WebhookSubscription.enabled.is_(True),
            or_(
                WebhookSubscription.user_id.is_(None),
                WebhookSubscription.user_id == user_id,
            ),
            or_(
                func.cardinality(WebhookSubscription.type_keys) == 0,
                literal(type_key) == any_(WebhookSubscription.type_keys),
            ),
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def set_enabled(self, sub_id: uuid.UUID, enabled: bool) -> WebhookSubscription | None:
        """@brief Toggle the enabled flag; returns the row or None."""
        return await self.update(sub_id, enabled=enabled)

    # update() takes (sub_id, **named fields); narrower than BaseRepository.update
    async def update(  # type: ignore[override]
        self,
        sub_id: uuid.UUID,
        url: str | None = None,
        type_keys: list[str] | None = None,
        enabled: bool | None = None,
    ) -> WebhookSubscription | None:
        """
        @brief Partially update a subscription (only non-None fields change).
        @return The updated row or None if missing.
        """
        sub = await self.get(sub_id)
        if sub is None:
            return None
        if url is not None:
            sub.url = url
        if type_keys is not None:
            sub.type_keys = type_keys
        if enabled is not None:
            sub.enabled = enabled
            if enabled:
                sub.failure_count = 0
        await self._session.flush()
        return sub

    async def delete(self, sub_id: uuid.UUID) -> bool:
        """@brief Hard-delete a subscription; True if it existed."""
        sub = await self.get(sub_id)
        if sub is None:
            return False
        await self._session.delete(sub)
        await self._session.flush()
        return True

    async def record_failure(self, sub_id: uuid.UUID) -> None:
        """@brief Increment failure_count; auto-disable at ``MAX_FAILURES``."""
        sub = await self.get(sub_id)
        if sub is None:
            return
        sub.failure_count += 1
        sub.last_failure_at = datetime.now(UTC)
        if sub.failure_count >= MAX_FAILURES:
            sub.enabled = False
        await self._session.flush()

    async def record_success(self, sub_id: uuid.UUID) -> None:
        """@brief Reset failure_count to 0."""
        sub = await self.get(sub_id)
        if sub is None:
            return
        sub.failure_count = 0
        await self._session.flush()
