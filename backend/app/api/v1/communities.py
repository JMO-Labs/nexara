"""
@file communities.py
@brief Community-level admin endpoints (webhook subscriptions).

Admin only (``require_role("admin")``); a user belongs to exactly one
community, so any other ``{community_id}`` is rejected with 403.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_webhook_service as _webhook_service
from app.core.dependencies import require_role
from app.core.exceptions import AppError
from app.core.i18n import _
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.webhook import (
    WebhookCreateRequest,
    WebhookCreateResponse,
    WebhookListItem,
    WebhookUpdateRequest,
)
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/communities", tags=["communities"])


async def _admin_of(community_id: uuid.UUID, user: User = Depends(require_role("admin"))) -> User:
    """@brief Ensure the admin belongs to the addressed community."""
    if user.community_id != community_id:
        raise AppError(
            code="WEBHOOK_FORBIDDEN",
            message=_("You can only manage webhooks of your own community"),
            status_code=403,
        )
    return user


@router.get("/{community_id}/webhooks", response_model=list[WebhookListItem])
async def list_community_webhooks(
    _admin: User = Depends(_admin_of),
    service: WebhookService = Depends(_webhook_service),
) -> list[WebhookListItem]:
    """@brief List community-level webhooks (no secrets)."""
    return [WebhookListItem.model_validate(s) for s in await service.list_for_community()]


@router.post(
    "/{community_id}/webhooks",
    response_model=WebhookCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_community_webhook(
    body: WebhookCreateRequest,
    _admin: User = Depends(_admin_of),
    service: WebhookService = Depends(_webhook_service),
) -> WebhookCreateResponse:
    """@brief Create a community-level webhook; secret returned once."""
    sub, secret = await service.create(None, body.url, body.type_keys)
    return WebhookCreateResponse(**WebhookListItem.model_validate(sub).model_dump(), secret=secret)


@router.patch("/{community_id}/webhooks/{webhook_id}", response_model=WebhookListItem)
async def update_community_webhook(
    webhook_id: uuid.UUID,
    body: WebhookUpdateRequest,
    _admin: User = Depends(_admin_of),
    service: WebhookService = Depends(_webhook_service),
) -> WebhookListItem:
    """@brief Partially update a community-level webhook."""
    sub = await service.update(
        None, webhook_id, url=body.url, type_keys=body.type_keys, enabled=body.enabled
    )
    return WebhookListItem.model_validate(sub)


@router.delete("/{community_id}/webhooks/{webhook_id}", response_model=MessageResponse)
async def delete_community_webhook(
    webhook_id: uuid.UUID,
    _admin: User = Depends(_admin_of),
    service: WebhookService = Depends(_webhook_service),
) -> MessageResponse:
    """@brief Delete a community-level webhook."""
    await service.delete(None, webhook_id)
    return MessageResponse(message=_("Webhook deleted"))
