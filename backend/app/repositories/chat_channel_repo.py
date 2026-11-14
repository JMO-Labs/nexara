"""
@file chat_channel_repo.py
@brief Chat channel repository (community / subgroup / direct channels).

DMs are resolved via the ``direct_message_participants`` join table using
a canonical (sorted) pair of user UUIDs. All reads apply ``community_id``
scoping.
"""

from __future__ import annotations

import uuid
from typing import Any, cast

from sqlalchemy import and_, or_, select
from sqlalchemy.engine import CursorResult

from app.models.chat import DirectMessageParticipant
from app.models.subgroup import ChatChannel
from app.models.user import User
from app.repositories.base import BaseRepository


class ChatChannelRepository(BaseRepository[ChatChannel]):
    """
    @brief Async repository for :class:`ChatChannel` operations.

    @param session Async SQLAlchemy session.
    """

    model = ChatChannel

    async def get(
        self,
        channel_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> ChatChannel | None:
        """
        @brief Fetch a channel by ID within a community.

        @param channel_id Channel UUID.
        @param community_id Community scope.
        @return Channel or None.
        """
        stmt = select(ChatChannel).where(
            ChatChannel.id == channel_id,
            ChatChannel.community_id == community_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_community_default(self, community_id: uuid.UUID) -> ChatChannel | None:
        """
        @brief Return the community-wide default channel, if any.

        @param community_id Community scope.
        @return The first ``community``-type channel (by created_at) or None.
        """
        stmt = (
            select(ChatChannel)
            .where(
                ChatChannel.community_id == community_id,
                ChatChannel.channel_type == "community",
            )
            .order_by(ChatChannel.created_at.asc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_user(
        self,
        channel_id: uuid.UUID,
        user_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> ChatChannel | None:
        """
        @brief Fetch a channel only if the given user is permitted to see it.

        Visibility rules:
          * ``community`` channels are visible to any authenticated member.
          * ``subgroup`` channels require a matching subgroup_members row.
          * ``direct`` channels require a row in ``direct_message_participants``.

        @param channel_id Channel UUID.
        @param user_id Requesting user UUID.
        @param community_id Community scope.
        @return Channel or None when the user cannot access it.
        """
        channel = await self.get(channel_id, community_id)
        if channel is None:
            return None

        if channel.channel_type == "community":
            return channel

        if channel.channel_type == "subgroup":
            from app.models.subgroup import SubgroupMember

            sg_stmt = select(SubgroupMember).where(
                SubgroupMember.subgroup_id == channel.subgroup_id,
                SubgroupMember.user_id == user_id,
            )
            sg_result = await self._session.execute(sg_stmt)
            return channel if sg_result.scalar_one_or_none() is not None else None

        if channel.channel_type == "direct":
            dm_stmt = select(DirectMessageParticipant).where(
                DirectMessageParticipant.channel_id == channel.id,
                DirectMessageParticipant.user_id == user_id,
            )
            dm_result = await self._session.execute(dm_stmt)
            return channel if dm_result.scalar_one_or_none() is not None else None

        return None

    async def remove_dm_participant(
        self,
        channel_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """
        @brief Remove ``user_id`` from a DM channel's participant list.

        Used to "delete" a DM thread for a single user. Returns True when
        a row was removed. Other participants retain access until they
        also leave.
        """
        from sqlalchemy import delete

        stmt = delete(DirectMessageParticipant).where(
            DirectMessageParticipant.channel_id == channel_id,
            DirectMessageParticipant.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return (cast(CursorResult[Any], result).rowcount or 0) > 0

    async def list_member_ids(
        self,
        channel: ChatChannel,
        community_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        """
        @brief Return user UUIDs allowed to receive realtime frames for this channel.

        Used by the chat service to fan out broadcasts via per-user pub/sub.
        """
        if channel.channel_type == "community":
            stmt = select(User.id).where(
                User.community_id == community_id,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
            result = await self._session.execute(stmt)
            return [row[0] for row in result.all()]

        if channel.channel_type == "subgroup":
            from app.models.subgroup import SubgroupMember

            stmt = select(SubgroupMember.user_id).where(
                SubgroupMember.subgroup_id == channel.subgroup_id,
            )
            result = await self._session.execute(stmt)
            return [row[0] for row in result.all()]

        if channel.channel_type == "direct":
            stmt = select(DirectMessageParticipant.user_id).where(
                DirectMessageParticipant.channel_id == channel.id,
            )
            result = await self._session.execute(stmt)
            return [row[0] for row in result.all()]

        return []

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> list[ChatChannel]:
        """
        @brief Return every channel the user can see (community, subgroup, direct).

        @param user_id User UUID.
        @param community_id Community scope.
        @return List of channels ordered by channel_type, created_at ASC.
        """
        from app.models.subgroup import SubgroupMember

        subgroup_member_ids = select(SubgroupMember.subgroup_id).where(
            SubgroupMember.user_id == user_id,
        )
        dm_channel_ids = select(DirectMessageParticipant.channel_id).where(
            DirectMessageParticipant.user_id == user_id,
        )

        stmt = (
            select(ChatChannel)
            .where(
                ChatChannel.community_id == community_id,
                or_(
                    ChatChannel.channel_type == "community",
                    and_(
                        ChatChannel.channel_type == "subgroup",
                        ChatChannel.subgroup_id.in_(subgroup_member_ids),
                    ),
                    and_(
                        ChatChannel.channel_type == "direct",
                        ChatChannel.id.in_(dm_channel_ids),
                    ),
                ),
            )
            .order_by(ChatChannel.channel_type.asc(), ChatChannel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_dm_threads(
        self,
        user_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> list[tuple[ChatChannel, User]]:
        """
        @brief List every DM thread the user participates in.

        Pairs each DM channel with the *other* participant's user row.

        @param user_id Requesting user UUID.
        @param community_id Community scope.
        @return List of ``(ChatChannel, peer_User)`` tuples newest first.
        """
        my_dm_ids = select(DirectMessageParticipant.channel_id).where(
            DirectMessageParticipant.user_id == user_id,
        )
        stmt = (
            select(ChatChannel, User)
            .join(
                DirectMessageParticipant,
                DirectMessageParticipant.channel_id == ChatChannel.id,
            )
            .join(User, User.id == DirectMessageParticipant.user_id)
            .where(
                ChatChannel.community_id == community_id,
                ChatChannel.channel_type == "direct",
                ChatChannel.id.in_(my_dm_ids),
                DirectMessageParticipant.user_id != user_id,
            )
            .order_by(ChatChannel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [(c, u) for c, u in result.all()]

    async def get_dm_peer_id(self, channel_id: uuid.UUID, user_id: uuid.UUID) -> uuid.UUID | None:
        """
        @brief Return the other participant of a DM channel.

        @param channel_id DM channel UUID.
        @param user_id The known participant.
        @return Peer UUID or None if not found.
        """
        stmt = select(DirectMessageParticipant.user_id).where(
            DirectMessageParticipant.channel_id == channel_id,
            DirectMessageParticipant.user_id != user_id,
        )
        result = await self._session.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    async def get_or_create_dm(
        self,
        user_a: uuid.UUID,
        user_b: uuid.UUID,
        community_id: uuid.UUID,
    ) -> tuple[ChatChannel, bool]:
        """
        @brief Return the DM channel shared by two users, creating it if absent.

        The canonical DM for a pair is determined by intersecting the
        ``direct_message_participants`` rows for both users: a channel
        shared by both is the existing thread, otherwise a new
        ``direct`` channel plus two participant rows are inserted.

        @param user_a First participant UUID.
        @param user_b Second participant UUID.
        @param community_id Community scope.
        @return ``(channel, created)`` tuple.
        """
        if user_a == user_b:
            raise ValueError("Cannot create DM with yourself")

        a_channels = select(DirectMessageParticipant.channel_id).where(
            DirectMessageParticipant.user_id == user_a,
        )
        b_channels = select(DirectMessageParticipant.channel_id).where(
            DirectMessageParticipant.user_id == user_b,
        )
        stmt = (
            select(ChatChannel)
            .where(
                ChatChannel.community_id == community_id,
                ChatChannel.channel_type == "direct",
                ChatChannel.id.in_(a_channels),
                ChatChannel.id.in_(b_channels),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            return (existing, False)

        # Build a deterministic name ``dm:{sorted_a}:{sorted_b}``.
        sorted_pair = sorted([user_a, user_b])
        channel = ChatChannel(
            community_id=community_id,
            name=f"dm:{sorted_pair[0]}:{sorted_pair[1]}",
            channel_type="direct",
            subgroup_id=None,
        )
        self._session.add(channel)
        await self._session.flush()
        await self._session.refresh(channel)

        self._session.add_all(
            [
                DirectMessageParticipant(channel_id=channel.id, user_id=user_a),
                DirectMessageParticipant(channel_id=channel.id, user_id=user_b),
            ]
        )
        await self._session.flush()
        return (channel, True)

    async def get_or_create_community_default(
        self,
        community_id: uuid.UUID,
        name: str = "General",
    ) -> tuple[ChatChannel, bool]:
        """
        @brief Return (creating if absent) the default community-level chat channel.

        Ensures every community has exactly one community-type channel as the
        default General channel for community-wide discussion.

        @param community_id Community scope.
        @param name Channel display name (defaults to "General").
        @return ``(channel, created)`` tuple.
        """
        stmt = (
            select(ChatChannel)
            .where(
                ChatChannel.community_id == community_id,
                ChatChannel.channel_type == "community",
                ChatChannel.subgroup_id.is_(None),
            )
            .order_by(ChatChannel.created_at.asc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            return (existing, False)

        channel = ChatChannel(
            community_id=community_id,
            name=name,
            channel_type="community",
            subgroup_id=None,
        )
        self._session.add(channel)
        await self._session.flush()
        await self._session.refresh(channel)
        return (channel, True)

    async def get_or_create_subgroup(
        self,
        subgroup_id: uuid.UUID,
        community_id: uuid.UUID,
        name: str,
    ) -> tuple[ChatChannel, bool]:
        """
        @brief Return (creating if absent) the chat channel for a subgroup.

        @param subgroup_id Subgroup UUID.
        @param community_id Community scope.
        @param name Channel display name (typically the subgroup name).
        @return ``(channel, created)`` tuple.
        """
        stmt = (
            select(ChatChannel)
            .where(
                ChatChannel.community_id == community_id,
                ChatChannel.channel_type == "subgroup",
                ChatChannel.subgroup_id == subgroup_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            return (existing, False)

        channel = ChatChannel(
            community_id=community_id,
            name=name,
            channel_type="subgroup",
            subgroup_id=subgroup_id,
        )
        self._session.add(channel)
        await self._session.flush()
        await self._session.refresh(channel)
        return (channel, True)
