"""
@file push.py
@brief Web Push API endpoints — VAPID key, subscribe, unsubscribe, list.

All endpoints require authentication.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.i18n import _
from app.models.user import User
from app.repositories.push_repo import PushSubscriptionRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.common import MessageResponse
from app.schemas.push import (
    PushSubscribeRequest,
    PushSubscriptionResponse,
    PushUnsubscribeRequest,
    VAPIDPublicKeyResponse,
)
from app.services.push_service import PushService

router = APIRouter(prefix="/push", tags=["push"])


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Extract the community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


def _build_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
    settings: Settings = Depends(get_settings),
) -> PushService:
    """@brief Build the PushService with injected dependencies."""
    return PushService(
        push_repo=PushSubscriptionRepository(db),
        settings_repo=SettingsRepository(db),
        community_id=community_id,
        settings=settings,
    )


@router.get("/vapid-key", response_model=VAPIDPublicKeyResponse)
async def get_vapid_key(
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> VAPIDPublicKeyResponse:
    """@brief Return the public VAPID key for client-side subscription."""
    return VAPIDPublicKeyResponse(public_key=settings.VAPID_PUBLIC_KEY)


@router.post("/subscribe", response_model=PushSubscriptionResponse, status_code=201)
async def subscribe(
    request: Request,
    body: PushSubscribeRequest,
    user: User = Depends(get_current_user),
    service: PushService = Depends(_build_service),
) -> PushSubscriptionResponse:
    """@brief Subscribe the current user to push notifications."""
    user_agent = request.headers.get("User-Agent")
    sub = await service.subscribe(
        user_id=user.id,
        endpoint=str(body.endpoint),
        p256dh=body.keys.p256dh,
        auth=body.keys.auth,
        user_agent=user_agent,
    )
    return PushSubscriptionResponse.model_validate(sub)


@router.delete("/subscribe", response_model=MessageResponse)
async def unsubscribe(
    body: PushUnsubscribeRequest,
    user: User = Depends(get_current_user),
    service: PushService = Depends(_build_service),
) -> MessageResponse:
    """@brief Unsubscribe the current user from push notifications."""
    await service.unsubscribe(user.id, body.endpoint)
    return MessageResponse(message=_("Unsubscribed"))


@router.get("/subscriptions", response_model=list[PushSubscriptionResponse])
async def list_subscriptions(
    user: User = Depends(get_current_user),
    service: PushService = Depends(_build_service),
) -> list[PushSubscriptionResponse]:
    """@brief List push subscriptions for the current user."""
    return await service.list_subscriptions(user.id)
