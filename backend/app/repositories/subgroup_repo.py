"""
@file subgroup_repo.py
@brief Repositories for subgroups, subgroup membership, and chat channels.

Provides DB access for the Subgroup and SubgroupMember models with
``community_id`` scoping and block-filter helpers.  Chat channel rows
are inserted here (as plain ORM rows) when a subgroup is created; the
chat API itself is implemented elsewhere.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import func, select

from app.models.subgroup import ChatChannel, Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.base import BaseRepository

logger = structlog.get_logger(__name__)


class SubgroupRepository(BaseRepository[Subgroup]):
    """
    @brief Async repository for Subgroup CRUD and discovery queries.

    @param session Async SQLAlchemy session.
    """

    model = Subgroup

    async def get_by_slug(
        self,
        slug: str,
        community_id: uuid.UUID,
    ) -> Subgroup | None:
        """
        @brief Fetch a subgroup by slug, scoped to the community.

        @param slug URL-safe subgroup identifier.
        @param community_id Community scope.
        @return The Subgroup or None.
        """
        stmt = self._base_query().where(
            Subgroup.slug == slug,
            Subgroup.community_id == community_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_visible_for_user(
        self,
        community_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        include_archived: bool = False,
        is_admin: bool = False,
    ) -> list[Subgroup]:
        """
        @brief List subgroups visible to the given user.

        Visibility rules:
          - Public (``is_private=False``) subgroups are always visible.
          - Private subgroups are visible only to members or admins.
          - Archived subgroups are excluded unless ``include_archived``.

        @param community_id Community scope.
        @param user_id Viewer user ID.
        @param include_archived When true, include archived subgroups.
        @param is_admin When true, admin bypass — return all subgroups.
        @return List of Subgroup rows ordered by created_at DESC.
        """
        stmt = select(Subgroup).where(Subgroup.community_id == community_id)

        if not include_archived:
            stmt = stmt.where(Subgroup.archived_at.is_(None))

        if not is_admin:
            # User sees: public subgroups OR private subgroups they belong to.
            member_subq = select(SubgroupMember.subgroup_id).where(
                SubgroupMember.user_id == user_id,
            )
            from sqlalchemy import or_

            stmt = stmt.where(
                or_(
                    Subgroup.is_private.is_(False),
                    Subgroup.id.in_(member_subq),
                )
            )

        stmt = stmt.order_by(Subgroup.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_subgroup(
        self,
        *,
        community_id: uuid.UUID,
        name: str,
        slug: str,
        description: str | None,
        avatar_url: str | None,
        is_private: bool,
        join_policy: str,
        created_by: uuid.UUID,
    ) -> Subgroup:
        """
        @brief Insert a new subgroup row.

        @return The created Subgroup (with server defaults populated).
        """
        subgroup = Subgroup(
            community_id=community_id,
            name=name,
            slug=slug,
            description=description,
            avatar_url=avatar_url,
            is_private=is_private,
            join_policy=join_policy,
            created_by=created_by,
        )
        return await self.create(subgroup)

    async def update_fields(
        self,
        subgroup: Subgroup,
        data: dict[str, Any],
    ) -> Subgroup:
        """
        @brief Apply partial updates to a subgroup.

        @param subgroup The ORM instance.
        @param data Dict of fields to update (already filtered).
        @return The updated instance.
        """
        return await self.update(subgroup, data)

    async def archive(self, subgroup: Subgroup) -> Subgroup:
        """
        @brief Mark a subgroup as archived by setting ``archived_at``.

        @param subgroup The ORM instance.
        @return The archived instance.
        """
        from datetime import UTC, datetime

        subgroup.archived_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(subgroup)
        return subgroup

    async def count_active_owned_by(
        self,
        user_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> int:
        """
        @brief Count active (non-archived) subgroups owned by a user.

        Ownership is determined by a ``SubgroupMember`` row with role
        ``owner`` — the creator is auto-added as ``owner`` on creation.

        @param user_id User ID.
        @param community_id Community scope.
        @return Integer count.
        """
        stmt = (
            select(func.count(Subgroup.id))
            .select_from(Subgroup)
            .join(SubgroupMember, SubgroupMember.subgroup_id == Subgroup.id)
            .where(
                Subgroup.community_id == community_id,
                Subgroup.archived_at.is_(None),
                SubgroupMember.user_id == user_id,
                SubgroupMember.role == "owner",
            )
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def create_chat_channel(
        self,
        *,
        community_id: uuid.UUID,
        subgroup_id: uuid.UUID,
        name: str,
    ) -> ChatChannel:
        """
        @brief Insert a chat channel row for a newly created subgroup.

        @param community_id Community scope.
        @param subgroup_id Subgroup the channel belongs to.
        @param name Human-readable channel name.
        @return The created ChatChannel.
        """
        channel = ChatChannel(
            community_id=community_id,
            name=name,
            channel_type="subgroup",
            subgroup_id=subgroup_id,
        )
        self._session.add(channel)
        await self._session.flush()
        await self._session.refresh(channel)
        return channel

    async def get_chat_channel(
        self,
        subgroup_id: uuid.UUID,
    ) -> ChatChannel | None:
        """
        @brief Fetch the chat channel associated with a subgroup.

        @param subgroup_id The subgroup's UUID.
        @return The ChatChannel or None.
        """
        stmt = select(ChatChannel).where(ChatChannel.subgroup_id == subgroup_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class SubgroupMemberRepository(BaseRepository[SubgroupMember]):
    """
    @brief Async repository for subgroup membership records.

    @param session Async SQLAlchemy session.
    """

    model = SubgroupMember

    async def get_membership(
        self,
        subgroup_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SubgroupMember | None:
        """
        @brief Fetch a single membership row.

        @param subgroup_id Subgroup ID.
        @param user_id User ID.
        @return The SubgroupMember or None.
        """
        stmt = select(SubgroupMember).where(
            SubgroupMember.subgroup_id == subgroup_id,
            SubgroupMember.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_member(
        self,
        *,
        community_id: uuid.UUID,
        subgroup_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "member",
        invited_by: uuid.UUID | None = None,
    ) -> SubgroupMember:
        """
        @brief Add a membership row.

        @return The created SubgroupMember.
        """
        member = SubgroupMember(
            community_id=community_id,
            subgroup_id=subgroup_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by,
        )
        self._session.add(member)
        await self._session.flush()
        await self._session.refresh(member)
        return member

    async def remove_member(
        self,
        subgroup_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """
        @brief Delete a membership row.

        @param subgroup_id Subgroup ID.
        @param user_id User ID.
        @return True if a row was deleted, False otherwise.
        """
        membership = await self.get_membership(subgroup_id, user_id)
        if membership is None:
            return False
        await self._session.delete(membership)
        await self._session.flush()
        return True

    async def update_role(
        self,
        membership: SubgroupMember,
        role: str,
    ) -> SubgroupMember:
        """
        @brief Update a member's role in place.

        @param membership The membership ORM instance.
        @param role New role string.
        @return The updated instance.
        """
        membership.role = role
        await self._session.flush()
        await self._session.refresh(membership)
        return membership

    async def count_for_user(
        self,
        user_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> int:
        """
        @brief Count active memberships for a user.

        Archived subgroups do not count toward the user's limit.

        @param user_id User ID.
        @param community_id Community scope.
        @return Integer count.
        """
        stmt = (
            select(func.count(SubgroupMember.subgroup_id))
            .select_from(SubgroupMember)
            .join(Subgroup, Subgroup.id == SubgroupMember.subgroup_id)
            .where(
                SubgroupMember.user_id == user_id,
                Subgroup.community_id == community_id,
                Subgroup.archived_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def count_members(self, subgroup_id: uuid.UUID) -> int:
        """
        @brief Count all members in a subgroup.

        @param subgroup_id Subgroup ID.
        @return Integer count.
        """
        stmt = select(func.count(SubgroupMember.user_id)).where(
            SubgroupMember.subgroup_id == subgroup_id,
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def list_members(
        self,
        subgroup_id: uuid.UUID,
    ) -> list[tuple[SubgroupMember, User]]:
        """
        @brief List members of a subgroup joined against users.

        @param subgroup_id Subgroup ID.
        @return List of ``(SubgroupMember, User)`` tuples ordered by
        joined_at DESC.
        """
        stmt = (
            select(SubgroupMember, User)
            .join(User, User.id == SubgroupMember.user_id)
            .where(
                SubgroupMember.subgroup_id == subgroup_id,
                User.deleted_at.is_(None),
            )
            .order_by(SubgroupMember.joined_at.desc())
        )
        result = await self._session.execute(stmt)
        return [(m, u) for m, u in result.all()]
