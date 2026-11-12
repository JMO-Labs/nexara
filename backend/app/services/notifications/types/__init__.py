"""@file Built-in notification types.

@brief Importing this package registers all 12 built-in types.
"""

from app.services.notifications.types import (  # noqa: F401
    comment,
    event_reminder,
    event_rsvp,
    gallery_activity,
    gallery_reminder,
    invite_accepted,
    mention,
    new_post,
    prompt,
    prompt_summary,
    reaction,
    system,
)

__all__ = [
    "comment",
    "event_reminder",
    "event_rsvp",
    "gallery_activity",
    "gallery_reminder",
    "invite_accepted",
    "mention",
    "new_post",
    "prompt",
    "prompt_summary",
    "reaction",
    "system",
]
