"""
@file post_extras.py
@brief Extra per-post fields for the feed: the kudos recipient and the
       celebrated person/pet. Household names and links show only to
       viewers who may see that member.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import HouseholdMember
from app.models.post import Post
from app.models.user import User
from app.repositories.household_repo import household_visible


async def post_extras(
    session: AsyncSession, posts: list[Post], viewer_id: uuid.UUID | None
) -> dict[uuid.UUID, dict[str, Any]]:
    """@return post id -> {recipient_id, recipient, celebration}"""
    user_ids = {p.recipient_id for p in posts if p.recipient_id}
    user_ids |= {p.celebrate_id for p in posts if p.celebrate_type == "user" and p.celebrate_id}
    users: dict[uuid.UUID, User] = {}
    if user_ids:
        rows = await session.execute(select(User).where(User.id.in_(user_ids)))
        users = {u.id: u for u in rows.scalars()}
    pet_ids = {p.celebrate_id for p in posts if p.celebrate_type == "household"}
    members: dict[uuid.UUID, HouseholdMember] = {}
    if pet_ids and viewer_id is not None:
        cid = posts[0].community_id
        found = await session.execute(
            select(HouseholdMember).where(
                HouseholdMember.id.in_(pet_ids), household_visible(viewer_id, cid)
            )
        )
        members = {m.id: m for m in found.scalars()}

    def person(u: User | None) -> dict[str, Any] | None:
        if u is None:
            return None
        return {
            "id": str(u.id),
            "username": u.username,
            "display_name": u.display_name,
            "avatar_url": u.avatar_url,
        }

    out: dict[uuid.UUID, dict[str, Any]] = {}
    for p in posts:
        extra: dict[str, Any] = {
            "recipient_id": str(p.recipient_id) if p.recipient_id else None,
            "recipient": person(users.get(p.recipient_id)) if p.recipient_id else None,
            "celebration": None,
            "countdown_id": str(p.countdown_id) if p.countdown_id else None,
        }
        if p.celebrate_type == "user" and p.celebrate_id in users:
            u = users[p.celebrate_id]
            extra["celebration"] = {
                "subject_type": "user",
                "subject_id": str(u.id),
                "occasion": p.celebrate_occasion,
                "name": u.display_name,
                "is_pet": False,
                "avatar_url": u.avatar_url,
                "photo_media_id": None,
                "link": f"/app/u/{u.username}",
            }
        elif p.celebrate_type == "household":
            m = members.get(p.celebrate_id)  # type: ignore[arg-type]
            extra["celebration"] = {
                "subject_type": "household",
                "subject_id": str(m.id) if m else None,
                "occasion": p.celebrate_occasion,
                "name": m.name if m else None,  # hidden from viewers who can't see them
                "is_pet": bool(m and m.kind == "pet"),
                "avatar_url": None,
                "photo_media_id": str(m.photo_media_id) if m and m.photo_media_id else None,
                "link": f"/app/household/{m.id}" if m else None,
            }
        out[p.id] = extra
    return out
