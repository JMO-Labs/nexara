"""
@file push.py
@brief Pydantic schemas for Web Push subscription and VAPID.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class PushKeys(BaseModel):
    """@brief Web Push subscription keys (p256dh, auth)."""

    p256dh: str
    auth: str


class PushSubscribeRequest(BaseModel):
    """@brief Request body for subscribing to push notifications."""

    endpoint: HttpUrl
    keys: PushKeys


class PushUnsubscribeRequest(BaseModel):
    """@brief Request body for unsubscribing from push notifications."""

    endpoint: str


class PushSubscriptionResponse(BaseModel):
    """@brief Response schema for a push subscription."""

    model_config = {"from_attributes": True}

    id: UUID
    endpoint: str
    user_agent: str | None
    created_at: datetime


class VAPIDPublicKeyResponse(BaseModel):
    """@brief Public VAPID key for client-side subscription."""

    public_key: str
