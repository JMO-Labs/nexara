"""
@file post_celebrate.py
@brief Celebrate posts: check whose occasion a post celebrates (a member
       the author has no block with, or a household member/pet the author
       can see; gotcha days are for pets) and tell them about it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.core.exceptions import ValidationError
from app.core.i18n import _
from app.models.user import User
from app.repositories.celebration_repo import CelebrationRepository
from app.schemas.post import CelebrateIn


@dataclass(frozen=True)
class Celebrated:
    """@brief A validated celebration subject."""

    subject_type: str
    subject_id: uuid.UUID
    occasion: str
    name: str
    notify_id: uuid.UUID  # the person, or the pet's owner


async def resolve(
    repo: CelebrationRepository, cid: uuid.UUID, actor: User, c: CelebrateIn
) -> Celebrated:
    """@throws ValidationError when the subject can't be celebrated by this actor"""
    if c.subject_type == "user":
        u = await repo.celebratable_user(cid, actor.id, c.subject_id)
        if u is None or c.occasion == "gotcha_day":
            raise ValidationError(message=_("You can't celebrate that"))
        return Celebrated("user", u.id, c.occasion, u.display_name, u.id)
    m = await repo.celebratable_household(cid, actor.id, c.subject_id)
    if m is None or (c.occasion == "gotcha_day" and m.kind != "pet"):
        raise ValidationError(message=_("You can't celebrate that"))
    return Celebrated("household", m.id, c.occasion, m.name, m.owner_id)


async def notify(notification: Any, actor: User, c: Celebrated, post_id: uuid.UUID) -> None:
    """@brief Tell the celebrated person (or the pet's owner), never the author."""
    if c.notify_id == actor.id:
        return
    message = (
        _("%(user)s is celebrating you") % {"user": actor.display_name}
        if c.subject_type == "user"
        else _("%(user)s is celebrating %(name)s") % {"user": actor.display_name, "name": c.name}
    )
    await notification.notify(
        user_id=c.notify_id,
        type="mention",
        payload={
            "post_id": str(post_id),
            "actor_name": actor.display_name,
            "message": message,
            "link": f"/app/post/{post_id}",
        },
        actor_id=actor.id,
    )
