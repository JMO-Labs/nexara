"""@file Channel protocol and result type.

@brief Contract every notification delivery channel implements.
"""

from dataclasses import dataclass
from typing import ClassVar, Protocol

from app.models.notification import Notification


@dataclass(frozen=True)
class ChannelResult:
    """@brief Outcome of a channel send; channels never raise."""

    ok: bool
    skipped_reason: str | None = None
    error: str | None = None


class Channel(Protocol):
    """@brief Delivery channel protocol."""

    key: ClassVar[str]

    async def send(self, notification: Notification) -> ChannelResult:
        """@brief Deliver a notification.

        @param notification The notification to deliver.
        @return ChannelResult describing success, skip or failure.
        """
        ...
