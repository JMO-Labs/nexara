"""@file apprise.py
@brief Apprise channel: fans out to the user's enabled Apprise URLs.
"""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import AsyncIterator, ClassVar

import structlog

from app.db.session import async_session_factory
from app.models.notification import Notification
from app.repositories.apprise_repo import AppriseRepository
from app.services.notifications.channels.base import ChannelResult
from app.tasks.notification_tasks import apprise_deliver

logger = structlog.get_logger(__name__)

RepoFactory = Callable[[], AbstractAsyncContextManager[AppriseRepository]]


@asynccontextmanager
async def _default_repo() -> AsyncIterator[AppriseRepository]:
    async with async_session_factory() as session:
        yield AppriseRepository(session)


class AppriseChannel:
    """@brief Enqueues one ``apprise_deliver`` task per enabled URL."""

    key: ClassVar[str] = "apprise"

    def __init__(self, repo_factory: RepoFactory = _default_repo) -> None:
        """@param repo_factory Async context manager yielding a repository."""
        self._repo_factory = repo_factory

    async def send(self, notification: Notification) -> ChannelResult:
        """@brief Enqueue deliveries; never raises (failures isolated).

        @param notification The notification to deliver.
        @return ok, skipped (``no_urls``) or failed result.
        """
        try:
            async with self._repo_factory() as repo:
                rows = await repo.list_for_user(notification.user_id, notification.community_id)
            if not rows:
                return ChannelResult(ok=True, skipped_reason="no_urls")
            title = notification.type.replace("_", " ").title()
            body = notification.payload.get("message", "")
            for row in rows:
                apprise_deliver.delay(str(row.id), str(notification.id), title, body)
            return ChannelResult(ok=True)
        except Exception as exc:
            logger.warning(
                "notif.channel.failed",
                channel=self.key,
                notification_id=str(notification.id),
                error=str(exc),
            )
            return ChannelResult(ok=False, error=str(exc))
