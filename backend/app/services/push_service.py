"""
@file push_service.py
@brief Business logic for Web Push subscriptions and delivery.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

import structlog

from app.core.exceptions import AppError, NotFoundError
from app.core.i18n import _
from app.models.device_token import DeviceToken
from app.models.notification import PushSubscription
from app.schemas.push import PushSubscriptionResponse

if TYPE_CHECKING:
    from app.repositories.device_token_repo import DeviceTokenRepo
    from app.repositories.push_repo import PushSubscriptionRepository
    from app.repositories.settings_repo import SettingsRepository

logger = structlog.get_logger(__name__)

PUSH_PREF_MAP = {
    "mention": "notif_mention_push",
    "comment": "notif_comment_push",
    "reaction": "notif_reaction_push",
    "new_post": "notif_new_post_push",
    "system": "notif_system_push",
    "invite_accepted": "notif_invite_accepted_push",
}


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
        )
        return await self._push_repo.create(sub)

    async def unsubscribe(self, user_id: uuid.UUID, endpoint: str) -> None:
        """
        @brief Unsubscribe a user from push notifications.

        @param user_id User UUID.
        @param endpoint Web Push endpoint URL.
        """
        await self._push_repo.delete_by_endpoint(endpoint)

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
    ) -> None:
        """
        @brief Send a Web Push notification to all subscriptions for a user.

        On 410 Gone from the push service, removes the stale subscription.

        @param user_id Recipient user UUID.
        @param title Notification title.
        @param body Notification body.
        @param url URL to open when clicked.
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

        payload = json.dumps({"title": title, "body": body, "url": url})
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
            except WebPushException as exc:
                resp = getattr(exc, "response", None)
                if resp is not None and getattr(resp, "status_code", None) == 410:
                    await self._push_repo.cleanup_stale(sub.endpoint)
                    logger.info("push_subscription_removed_410", endpoint=sub.endpoint)
                else:
                    logger.warning("push_send_failed", endpoint=sub.endpoint, error=str(exc))

    async def should_send_push(self, user_id: uuid.UUID, notification_type: str) -> bool:
        """
        @brief Check if push should be sent based on user settings.

        @param user_id User UUID.
        @param notification_type Type (mention, comment, etc.).
        @return True if push should be sent.
        """
        if notification_type not in PUSH_PREF_MAP:
            return False

        settings = await self._settings_repo.get_by_user_id(user_id)
        if settings is None:
            return True

        if getattr(settings, "mute_all_push", False):
            return False

        pref_key = PUSH_PREF_MAP[notification_type]
        return bool(getattr(settings, pref_key, True))
