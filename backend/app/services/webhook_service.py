"""
@file webhook_service.py
@brief Webhook subscription management with ownership checks.
"""

from __future__ import annotations

import secrets
import uuid

from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.models.webhook import WebhookSubscription
from app.repositories.webhook_repo import WebhookRepository


class WebhookService:
    """
    @brief CRUD for webhook subscriptions.

    ``owner_id`` is the user id for user-level subscriptions, or None for
    community-level ones; a row is only reachable through its own scope.
    """

    def __init__(self, repo: WebhookRepository, community_id: uuid.UUID) -> None:
        self._repo = repo
        self._community_id = community_id

    async def list_for_user(self, user_id: uuid.UUID) -> list[WebhookSubscription]:
        """@brief User-level subscriptions."""
        return await self._repo.list_for_user(user_id)

    async def list_for_community(self) -> list[WebhookSubscription]:
        """@brief Community-level subscriptions."""
        return await self._repo.list_for_community(self._community_id)

    async def create(
        self, owner_id: uuid.UUID | None, url: str, type_keys: list[str]
    ) -> tuple[WebhookSubscription, str]:
        """
        @brief Create a subscription with a fresh random secret.
        @return (row, plaintext secret) — the secret is not retrievable later.
        """
        secret = secrets.token_urlsafe(32)
        sub = await self._repo.create(self._community_id, owner_id, url, secret, type_keys)
        return sub, secret

    async def _owned(self, owner_id: uuid.UUID | None, sub_id: uuid.UUID) -> WebhookSubscription:
        sub = await self._repo.get(sub_id)
        if sub is None or sub.community_id != self._community_id or sub.user_id != owner_id:
            raise NotFoundError(_("Webhook not found"))
        return sub

    async def update(
        self,
        owner_id: uuid.UUID | None,
        sub_id: uuid.UUID,
        url: str | None = None,
        type_keys: list[str] | None = None,
        enabled: bool | None = None,
    ) -> WebhookSubscription:
        """@brief Partially update an owned subscription."""
        await self._owned(owner_id, sub_id)
        updated = await self._repo.update(sub_id, url=url, type_keys=type_keys, enabled=enabled)
        if updated is None:
            raise NotFoundError(_("Webhook not found"))
        return updated

    async def delete(self, owner_id: uuid.UUID | None, sub_id: uuid.UUID) -> None:
        """@brief Delete an owned subscription."""
        await self._owned(owner_id, sub_id)
        await self._repo.delete(sub_id)
