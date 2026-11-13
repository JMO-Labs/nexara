"""@file Built-in notification types.

@brief Importing this package registers all 16 built-in types.
"""

from app.services.notifications.types import (  # noqa: F401
    birthday_reminder,
    comment,
    event_reminder,
    event_rsvp,
    gallery_activity,
    gallery_reminder,
    gentle_nudge,
    invite_accepted,
    kudos_received,
    list_completed,
    mention,
    new_post,
    nudge_received,
    prompt,
    prompt_summary,
    reaction,
    system,
)

__all__ = [
    "birthday_reminder",
    "comment",
    "event_reminder",
    "event_rsvp",
    "gallery_activity",
    "gallery_reminder",
    "gentle_nudge",
    "invite_accepted",
    "kudos_received",
    "list_completed",
    "mention",
    "new_post",
    "nudge_received",
    "prompt",
    "prompt_summary",
    "reaction",
    "system",
]
