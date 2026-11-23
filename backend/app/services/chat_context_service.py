"""
@file chat_context_service.py
@brief Builds the conversation details payload (participants only), applying
       the privacy rules for presence, local time and birthdays.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.models.user import User
from app.repositories.chat_channel_repo import ChatChannelRepository
from app.repositories.chat_context_repo import ChatContextRepository, PeerRow
from app.schemas.chat_context import (
    ContextEvent,
    ContextGroup,
    ContextList,
    ContextMember,
    ContextPeer,
    DmContext,
    GroupContext,
)


def days_until_birthday(birthday: date, today: date) -> int:
    """@brief Days to the next birthday (Feb 29 falls on Feb 28 in common years)."""

    def on(year: int) -> date:
        try:
            return birthday.replace(year=year)
        except ValueError:
            return date(year, 2, 28)

    nxt = on(today.year)
    if nxt < today:
        nxt = on(today.year + 1)
    return (nxt - today).days


def _tz(name: str | None) -> ZoneInfo | None:
    """@brief Resolve an IANA zone or None."""
    if not name:
        return None
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None


class ChatContextService:
    """
    @param channel_repo Channel repo (participant check).
    @param repo Context repo.
    @param community_id Community scope.
    """

    def __init__(
        self,
        channel_repo: ChatChannelRepository,
        repo: ChatContextRepository,
        community_id: uuid.UUID,
    ) -> None:
        self._channels = channel_repo
        self._repo = repo
        self._community_id = community_id

    async def get_context(self, viewer: User, channel_id: uuid.UUID) -> DmContext | GroupContext:
        """
        @brief Details for a channel the viewer participates in.
        @raises NotFoundError If the channel is unknown or not accessible.
        """
        channel = await self._channels.get_for_user(channel_id, viewer.id, self._community_id)
        if channel is None:
            raise NotFoundError(_("Channel not found"))
        now = datetime.now(UTC)
        if channel.channel_type == "direct":
            return await self._dm(viewer, channel.id, now)
        return await self._group(viewer, channel.subgroup_id, now)

    def _peer_card(self, viewer: User, p: PeerRow, now: datetime) -> ContextPeer:
        """@brief Peer card with each field gated by the peer's privacy flags."""
        if p.blocked or p.memorialized:
            return ContextPeer(id=p.id, display_name=p.display_name, username=p.username)
        tz = _tz(p.timezone)
        today = now.astimezone(_tz(viewer.timezone) or UTC).date()
        shared_bday = p.birthday is not None and p.show_birthday_to == "community"
        return ContextPeer(
            id=p.id,
            display_name=p.display_name,
            username=p.username,
            avatar_url=p.avatar_url,
            last_seen_at=p.last_seen_at if p.show_last_seen else None,
            local_time_tz=p.timezone if (p.show_online_status and tz) else None,
            birthday_in_days=(
                days_until_birthday(p.birthday, today) if shared_bday and p.birthday else None
            ),
        )

    async def _dm(self, viewer: User, channel_id: uuid.UUID, now: datetime) -> DmContext:
        peer = await self._repo.dm_peer(channel_id, viewer.id, self._community_id)
        if peer is None:
            raise NotFoundError(_("Channel not found"))
        card = self._peer_card(viewer, peer, now)
        if peer.blocked or peer.memorialized:
            return DmContext(peer=card)
        groups = await self._repo.shared_groups(viewer.id, peer.id, self._community_id)
        events = await self._repo.shared_events(viewer.id, peer.id, self._community_id, now)
        return DmContext(
            peer=card,
            shared_groups=[ContextGroup(id=g.id, name=g.name, slug=g.slug) for g in groups],
            upcoming_events=[
                ContextEvent(id=e.id, title=e.title, starts_at=e.starts_at) for e in events
            ],
        )

    async def _group(
        self, viewer: User, subgroup_id: uuid.UUID | None, now: datetime
    ) -> GroupContext:
        users, total = await self._repo.members(viewer.id, self._community_id, subgroup_id)
        out = GroupContext(
            members=[
                ContextMember(id=u.id, display_name=u.display_name, avatar_url=u.avatar_url)
                for u in users
            ],
            member_count=total,
        )
        if subgroup_id is None:
            return out
        ev = await self._repo.next_group_event(viewer.id, self._community_id, subgroup_id, now)
        if ev is not None:
            out.next_event = ContextEvent(id=ev.id, title=ev.title, starts_at=ev.starts_at)
        lists = await self._repo.open_lists(viewer.id, self._community_id, subgroup_id)
        out.open_lists = [
            ContextList(id=x.id, title=x.title, item_count=x.item_count) for x in lists
        ]
        return out
