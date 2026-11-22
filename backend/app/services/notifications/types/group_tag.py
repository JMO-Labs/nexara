"""@file Built-in `group_tag` notification type.

@brief Payload schema and registration for `group_tag` (someone @-tagged a
       group you belong to). Separate from `mention` so members can mute it.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class GroupTagPayload(NotificationPayload):
    """@brief Payload for group_tag notifications."""

    actor_name: str
    group_name: str


GROUP_TAG_TYPE = NotificationType(
    key="group_tag",
    category="social",
    payload_schema=GroupTagPayload,
    default_channels={"inapp": True, "email": False, "push": True, "toast": False},
    group_window_seconds=None,
    toast_on_arrival=False,
    label_i18n="notif.group_tag.label",
    icon="users",
)
register(GROUP_TAG_TYPE)
