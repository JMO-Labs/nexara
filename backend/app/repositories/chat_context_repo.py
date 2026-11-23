"""
@file chat_context_repo.py
@brief Read-only lookups for the chat details panel. Every query is
       community-scoped and visibility/block filtered for the viewer.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import DirectMessageParticipant
from app.models.event import Event, EventAttendance
from app.models.list import List, ListMember
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.visibility_preds import my_subgroup_ids, not_blocked


@dataclass
class PeerRow:
    """@brief Peer user with raw privacy flags and a block marker."""

    id: uuid.UUID
    display_name: str
    username: str
    avatar_url: str | None
    last_seen_at: datetime | None
    timezone: str | None
    birthday: date | None
    memorialized: bool
    show_online_status: bool
    show_last_seen: bool
    show_birthday_to: str
    blocked: bool


def _event_visible(viewer_id: uuid.UUID) -> Any:
    """@brief Event the viewer may open (mirrors EventRepository.list_in_range)."""
    return or_(
        and_(Event.visibility == "community", Event.subgroup_id.is_(None)),
        and_(Event.visibility == "private", Event.author_id == viewer_id),
        and_(Event.visibility == "subgroup", Event.subgroup_id.in_(my_subgroup_ids(viewer_id))),
    )


class ChatContextRepository:
    """@brief Queries behind the conversation details panel."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def dm_peer(
        self, channel_id: uuid.UUID, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> PeerRow | None:
        """@brief The other participant of a DM, or None (peer left/deleted)."""
        blocked = ~not_blocked(User.id, viewer_id)
        stmt = (
            select(
                User,
                UserSettings.show_online_status,
                UserSettings.show_last_seen,
                UserSettings.show_birthday_to,
                blocked,
            )
            .join(DirectMessageParticipant, DirectMessageParticipant.user_id == User.id)
            .outerjoin(UserSettings, UserSettings.user_id == User.id)
            .where(
                DirectMessageParticipant.channel_id == channel_id,
                User.id != viewer_id,
                User.community_id == community_id,
                User.deleted_at.is_(None),
            )
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        u = row[0]
        return PeerRow(
            id=u.id,
            display_name=u.display_name,
            username=u.username,
            avatar_url=u.avatar_url,
            last_seen_at=u.last_seen_at,
            timezone=u.timezone,
            birthday=u.birthday,
            memorialized=u.memorialized_at is not None,
            show_online_status=True if row[1] is None else bool(row[1]),
            show_last_seen=True if row[2] is None else bool(row[2]),
            show_birthday_to=row[3] or "community",
            blocked=bool(row[4]),
        )

    async def shared_groups(
        self, viewer_id: uuid.UUID, peer_id: uuid.UUID, community_id: uuid.UUID
    ) -> list[Subgroup]:
        """@brief Active subgroups both users belong to."""
        theirs = select(SubgroupMember.subgroup_id).where(SubgroupMember.user_id == peer_id)
        stmt = (
            select(Subgroup)
            .where(
                Subgroup.community_id == community_id,
                Subgroup.archived_at.is_(None),
                Subgroup.id.in_(my_subgroup_ids(viewer_id)),
                Subgroup.id.in_(theirs),
            )
            .order_by(Subgroup.name)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def shared_events(
        self,
        viewer_id: uuid.UUID,
        peer_id: uuid.UUID,
        community_id: uuid.UUID,
        now: datetime,
        limit: int = 3,
    ) -> list[Event]:
        """@brief Upcoming events both users attend and the viewer may see."""
        peer_in = exists().where(
            EventAttendance.event_id == Event.id,
            EventAttendance.user_id == peer_id,
            EventAttendance.status == "attending",
        )
        me_in = exists().where(
            EventAttendance.event_id == Event.id,
            EventAttendance.user_id == viewer_id,
            EventAttendance.status == "attending",
        )
        stmt = (
            select(Event)
            .where(
                Event.community_id == community_id,
                Event.starts_at >= now,
                Event.source_removed.is_(False),
                peer_in,
                me_in,
                _event_visible(viewer_id),
            )
            .order_by(Event.starts_at)
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def members(
        self,
        viewer_id: uuid.UUID,
        community_id: uuid.UUID,
        subgroup_id: uuid.UUID | None,
        limit: int = 50,
    ) -> tuple[list[User], int]:
        """@brief Unblocked live members (subgroup or whole community) + total."""
        conds: list[Any] = [
            User.community_id == community_id,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
            or_(User.id == viewer_id, not_blocked(User.id, viewer_id)),
        ]
        if subgroup_id is not None:
            conds.append(
                User.id.in_(
                    select(SubgroupMember.user_id).where(SubgroupMember.subgroup_id == subgroup_id)
                )
            )
        total = (
            await self._session.execute(select(func.count(User.id)).where(*conds))
        ).scalar_one()
        stmt = select(User).where(*conds).order_by(User.display_name).limit(limit)
        return list((await self._session.execute(stmt)).scalars().all()), int(total)

    async def next_group_event(
        self,
        viewer_id: uuid.UUID,
        community_id: uuid.UUID,
        subgroup_id: uuid.UUID,
        now: datetime,
    ) -> Event | None:
        """@brief Soonest upcoming event of the subgroup the viewer may see."""
        stmt = (
            select(Event)
            .where(
                Event.community_id == community_id,
                Event.subgroup_id == subgroup_id,
                Event.starts_at >= now,
                Event.source_removed.is_(False),
                _event_visible(viewer_id),
            )
            .order_by(Event.starts_at)
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def open_lists(
        self,
        viewer_id: uuid.UUID,
        community_id: uuid.UUID,
        subgroup_id: uuid.UUID,
        limit: int = 5,
    ) -> list[List]:
        """@brief Active subgroup lists the viewer may open (list service rules)."""
        listed = exists().where(ListMember.list_id == List.id, ListMember.user_id == viewer_id)
        visible = or_(
            List.visibility == "community",
            and_(List.visibility == "private", List.owner_id == viewer_id),
            and_(List.visibility == "subgroup", List.subgroup_id.in_(my_subgroup_ids(viewer_id))),
            and_(List.visibility == "members", or_(List.owner_id == viewer_id, listed)),
        )
        stmt = (
            select(List)
            .where(
                List.community_id == community_id,
                List.subgroup_id == subgroup_id,
                List.deleted_at.is_(None),
                List.status == "active",
                visible,
            )
            .order_by(List.updated_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())
