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
from app.repositories.device_token_repo import DeviceTokenRepo
from app.repositories.push_repo import PushSubscriptionRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.common import MessageResponse
from app.schemas.push import (
    DeviceRegisterRequest,
    DeviceTokenResponse,
    PushDeviceRename,
    PushDeviceResponse,
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
        device_repo=DeviceTokenRepo(db),
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


@router.get("/devices", response_model=list[PushDeviceResponse])
async def list_devices(
    user: User = Depends(get_current_user),
    service: PushService = Depends(_build_service),
) -> list[PushDeviceResponse]:
    """@brief List the caller's push devices (no endpoint or keys)."""
    return await service.list_devices(user.id)


@router.patch("/devices/{device_id}", response_model=PushDeviceResponse)
async def rename_device(
    device_id: uuid.UUID,
    body: PushDeviceRename,
    user: User = Depends(get_current_user),
    service: PushService = Depends(_build_service),
) -> PushDeviceResponse:
    """@brief Rename one of the caller's push devices."""
    return await service.rename_device(user.id, device_id, body.name)


@router.post("/devices", response_model=DeviceTokenResponse, status_code=201)
async def register_device(
    body: DeviceRegisterRequest,
    user: User = Depends(get_current_user),
    service: PushService = Depends(_build_service),
) -> DeviceTokenResponse:
    """@brief Register (upsert) a native push device token for the current user."""
    device = await service.register_device(user.id, body.platform, body.token)
    return DeviceTokenResponse.model_validate(device)


@router.delete("/devices/{token}", response_model=MessageResponse)
async def unregister_device(
    token: str,
    user: User = Depends(get_current_user),
    service: PushService = Depends(_build_service),
) -> MessageResponse:
    """@brief Remove the caller's device; 404 if not theirs.

    A UUID path removes a Web Push device by id; anything else is a native
    (FCM) token, which is soft-deleted.
    """
    try:
        device_id = uuid.UUID(token)
    except ValueError:
        await service.unregister_device(user.id, token)
        return MessageResponse(message=_("Device unregistered"))
    await service.delete_device(user.id, device_id)
    return MessageResponse(message=_("Device removed"))
