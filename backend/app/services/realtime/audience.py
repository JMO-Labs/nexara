"""
@file audience.py
@brief Resolve who may receive a realtime event for a piece of content.

Feed events must never reach users who cannot see the content (subgroup or
private posts) or who are blocked by/blocking the author.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.moderation import UserBlock
from app.models.subgroup import SubgroupMember
from app.models.user import User
from app.services.realtime.events import EventType, RealtimeEvent, UserTarget


async def resolve_audience(
    session: AsyncSession,
    community_id: UUID,
    *,
    visibility: str,
    subgroup_id: UUID | None,
    author_id: UUID,
) -> list[UUID]:
    """
    @brief Compute the user ids allowed to receive events for content.

    @param session Active DB session.
    @param community_id Community scope.
    @param visibility ``community``, ``subgroup`` or ``private``.
    @param subgroup_id Subgroup for ``subgroup`` visibility.
    @param author_id Content author; always included.
    @return Distinct user ids, author first; blocked relations excluded.
    """
    if visibility == "community":
        stmt = select(User.id).where(
            User.community_id == community_id,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
    elif visibility == "subgroup" and subgroup_id is not None:
        stmt = select(SubgroupMember.user_id).where(
            SubgroupMember.subgroup_id == subgroup_id,
            SubgroupMember.community_id == community_id,
        )
    else:
        return [author_id]

    members = set((await session.execute(stmt)).scalars().all())

    blocks = select(
        select(UserBlock.blocked_id)
        .where(UserBlock.blocker_id == author_id, UserBlock.community_id == community_id)
        .union(
            select(UserBlock.blocker_id).where(
                UserBlock.blocked_id == author_id, UserBlock.community_id == community_id
            )
        )
        .subquery()
    )
    members -= set((await session.execute(blocks)).scalars().all())
    members.discard(author_id)
    return [author_id, *members]


async def emit_to_audience(
    event_bus: Any,
    audience: list[UUID],
    type: EventType,  # noqa: A002
    payload: dict[str, Any],
) -> None:
    """
    @brief Emit one event per audience member via the event bus.

    @param event_bus EventBus (or compatible) with ``emit``.
    @param audience Recipient user ids.
    @param type Event type.
    @param payload JSON-serializable payload.
    """
    for user_id in audience:
        await event_bus.emit(
            RealtimeEvent(type=type, target=UserTarget(user_id=user_id), payload=payload)
        )
