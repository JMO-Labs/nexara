"""
@file push_service.py
@brief Business logic for Web Push subscriptions and delivery.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import TYPE_CHECKING

import structlog

from app.core.exceptions import AppError, NotFoundError
from app.core.i18n import _
from app.models.device_token import DeviceToken
from app.models.notification import PushSubscription
from app.schemas.push import PushDeviceResponse, PushSubscriptionResponse
from app.services.auth.device import parse_device

if TYPE_CHECKING:
    from app.repositories.device_token_repo import DeviceTokenRepo
    from app.repositories.push_repo import PushSubscriptionRepository
    from app.repositories.settings_repo import SettingsRepository

logger = structlog.get_logger(__name__)


def endpoint_hash(endpoint: str) -> str:
    """@brief Short stable id of a push endpoint (lets a client spot its own device)."""
    return hashlib.sha256(endpoint.encode()).hexdigest()[:16]


def _device(sub: PushSubscription) -> PushDeviceResponse:
    """@brief Map a subscription to its secret-free device view."""
    return PushDeviceResponse(
        id=sub.id,
        name=sub.name or parse_device(sub.user_agent),
        endpoint_hash=endpoint_hash(sub.endpoint),
        created_at=sub.created_at,
        last_used_at=sub.last_used_at,
    )


class PushService:
    """
    @brief Service for Web Push subscription management and delivery.

    @param push_repo PushSubscriptionRepository instance.
    @param settings_repo SettingsRepository instance.
    @param community_id Community scope.
    @param settings Application settings (VAPID keys).
    @param device_repo Optional DeviceTokenRepo for native device tokens.
    """

    def __init__(
        self,
        push_repo: PushSubscriptionRepository,
        settings_repo: SettingsRepository,
        community_id: uuid.UUID,
        *,
        settings: object,
        device_repo: DeviceTokenRepo | None = None,
    ) -> None:
        self._push_repo = push_repo
        self._settings_repo = settings_repo
        self._community_id = community_id
        self._settings = settings
        self._device_repo = device_repo

    async def subscribe(
        self,
        user_id: uuid.UUID,
        endpoint: str,
        p256dh: str,
        auth: str,
        user_agent: str | None = None,
    ) -> PushSubscription:
        """
        @brief Subscribe a user to push notifications (upsert by endpoint).

        Deletes any existing subscription with the same endpoint, then creates new.

        @param user_id User UUID.
        @param endpoint Web Push endpoint URL.
        @param p256dh Public key from subscription.
        @param auth Auth secret from subscription.
        @param user_agent Optional User-Agent string.
        @return The created PushSubscription.
        """
        existing = await self._push_repo.find_by_endpoint(endpoint)
        if existing:
            await self._push_repo.delete_by_endpoint(endpoint)

        sub = PushSubscription(
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            user_agent=user_agent,
            name=parse_device(user_agent),
        )
        return await self._push_repo.create(sub)

    async def unsubscribe(self, user_id: uuid.UUID, endpoint: str) -> None:
        """
        @brief Unsubscribe a user from push notifications.

        @param user_id User UUID.
        @param endpoint Web Push endpoint URL.
        """
        await self._push_repo.delete_by_endpoint(endpoint, user_id=user_id)

    async def register_device(self, user_id: uuid.UUID, platform: str, token: str) -> DeviceToken:
        """
        @brief Upsert a native push device token for a user.

        @param user_id Owner UUID.
        @param platform ``android`` or ``ios``.
        @param token FCM device token.
        @return The stored DeviceToken.
        """
        repo = self._require_device_repo()
        existing = await repo.find_by_token(token)
        if existing:
            return await repo.reassign(
                existing,
                user_id=user_id,
                community_id=self._community_id,
                platform=platform,
            )
        device = DeviceToken(
            user_id=user_id,
            community_id=self._community_id,
            platform=platform,
            token=token,
        )
        return await repo.create(device)

    async def unregister_device(self, user_id: uuid.UUID, token: str) -> None:
        """
        @brief Soft-delete the caller's device token.

        @param user_id Owner UUID.
        @param token Device token string.
        @raise NotFoundError If the token is not an active token of the caller.
        """
        repo = self._require_device_repo()
        device = await repo.find_active(self._community_id, user_id, token)
        if device is None:
            raise NotFoundError(_("Device token not found"))
        await repo.soft_delete(device)

    def _require_device_repo(self) -> DeviceTokenRepo:
        """
        @brief Return the device repo or fail with a standard AppError.

        @return The configured DeviceTokenRepo.
        @raise AppError If the service was built without a device repo.
        """
        if self._device_repo is None:
            raise AppError(
                code="DEVICE_REPO_UNAVAILABLE",
                message=_("Device token storage is not configured"),
            )
        return self._device_repo

    async def list_subscriptions(self, user_id: uuid.UUID) -> list[PushSubscriptionResponse]:
        """
        @brief List all push subscriptions for a user.

        @param user_id User UUID.
        @return List of subscription responses.
        """
        subs = await self._push_repo.list_for_user(user_id)
        return [PushSubscriptionResponse.model_validate(s) for s in subs]

    async def send_push(
        self,
        user_id: uuid.UUID,
        title: str,
        body: str,
        url: str,
        *,
        tag: str | None = None,
        badge_count: int | None = None,
    ) -> None:
        """
        @brief Send a Web Push notification to all subscriptions for a user.

        On 404/410 from the push service, removes the stale subscription.

        @param user_id Recipient user UUID.
        @param title Notification title.
        @param body Notification body.
        @param url URL to open when clicked.
        @param tag Collapse key so repeat notifications stack.
        @param badge_count Unread in-app count for the app badge.
        """
        subs = await self._push_repo.list_for_user(user_id)
        if not subs:
            return

        vapid_private = getattr(self._settings, "VAPID_PRIVATE_KEY", "")
        vapid_public = getattr(self._settings, "VAPID_PUBLIC_KEY", "")
        smtp_from = getattr(self._settings, "SMTP_FROM", "") or "noreply@example.com"
        if not vapid_private or not vapid_public:
            logger.warning("push_vapid_not_configured")
            return

        data: dict[str, object] = {"title": title, "body": body, "url": url}
        if tag is not None:
            data["tag"] = tag
        if badge_count is not None:
            data["badge_count"] = badge_count
        payload = json.dumps(data)
        vapid_sub = f"mailto:{smtp_from}" if smtp_from else "mailto:noreply@example.com"

        from pywebpush import WebPushException, webpush

        for sub in subs:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                    },
                    data=payload,
                    vapid_private_key=vapid_private,
                    vapid_claims={"sub": vapid_sub},
                )
                await self._push_repo.touch_last_used(sub.id)
            except WebPushException as exc:
                resp = getattr(exc, "response", None)
                if resp is not None and getattr(resp, "status_code", None) in (404, 410):
                    await self._push_repo.cleanup_stale(sub.endpoint)
                    logger.info("push_subscription_removed", endpoint=sub.endpoint)
                else:
                    logger.warning("push_send_failed", endpoint=sub.endpoint, error=str(exc))

    async def list_devices(self, user_id: uuid.UUID) -> list[PushDeviceResponse]:
        """
        @brief List the caller's push devices (no endpoint or keys).

        @param user_id Owner UUID.
        @return Device views, newest first.
        """
        subs = await self._push_repo.list_devices(user_id, self._community_id)
        return [_device(s) for s in subs]

    async def rename_device(
        self, user_id: uuid.UUID, device_id: uuid.UUID, name: str
    ) -> PushDeviceResponse:
        """
        @brief Rename one of the caller's push devices.

        @raise NotFoundError If the device is not the caller's.
        """
        sub = await self._push_repo.get_device(device_id, user_id, self._community_id)
        if sub is None:
            raise NotFoundError(_("Device not found"))
        sub.name = name
        return _device(sub)

    async def delete_device(self, user_id: uuid.UUID, device_id: uuid.UUID) -> None:
        """
        @brief Remove one of the caller's push devices.

        @raise NotFoundError If the device is not the caller's.
        """
        if not await self._push_repo.delete_device(device_id, user_id, self._community_id):
            raise NotFoundError(_("Device not found"))
