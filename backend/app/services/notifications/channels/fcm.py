"""@file FCM (Firebase Cloud Messaging) notification channel.

@brief Delivers push to a user's registered mobile device tokens. Gated by
the user's ``push`` preference in the dispatcher.
"""

from typing import ClassVar, Protocol

import structlog

from app.models.notification import Notification
from app.repositories.device_token_repo import DeviceTokenRepo
from app.services.notifications.channels.base import ChannelResult

logger = structlog.get_logger(__name__)


class FCMTokenInvalidError(Exception):
    """@brief Raised by an FCM client when a token is unregistered/invalid."""


class FCMClient(Protocol):
    """@brief Injectable FCM transport."""

    async def send(self, token: str, title: str, body: str, data: dict[str, str]) -> None:
        """@brief Send one message; raise FCMTokenInvalidError for dead tokens."""
        ...


class FCMChannel:
    """@brief Sends a notification to each active device token via FCM."""

    key: ClassVar[str] = "fcm"

    def __init__(
        self, client: FCMClient, repo: DeviceTokenRepo, credentials_file: str | None
    ) -> None:
        """
        @param client FCM transport.
        @param repo Device token repository.
        @param credentials_file Value of FCM_CREDENTIALS_FILE; None disables.
        """
        self._client = client
        self._repo = repo
        self._creds = credentials_file

    async def send(self, notification: Notification) -> ChannelResult:
        """@brief Send to all active tokens; soft-delete rejected ones; never raises.

        @param notification The notification to deliver.
        @return ok, skipped (unconfigured / no devices) or failed result.
        """
        if not self._creds:
            return ChannelResult(ok=False, skipped_reason="fcm_not_configured")
        try:
            devices = await self._repo.list_active_for_user(
                notification.community_id, notification.user_id
            )
            if not devices:
                return ChannelResult(ok=False, skipped_reason="no_devices")
            title = notification.type.replace("_", " ").title()
            body = str(notification.payload.get("message", ""))
            data = {"type": notification.type, "url": str(notification.payload.get("link") or "")}
            for dev in devices:
                try:
                    await self._client.send(dev.token, title, body, data)
                except FCMTokenInvalidError:
                    await self._repo.soft_delete(dev)
            return ChannelResult(ok=True)
        except Exception as exc:
            logger.warning(
                "notif.channel.failed",
                channel=self.key,
                notification_id=str(notification.id),
                error=str(exc),
            )
            return ChannelResult(ok=False, error=str(exc))
