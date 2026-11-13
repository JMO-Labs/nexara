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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.media import Media
from app.models.subgroup import ChatChannel, Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.base import BaseRepository

# Maximum depth used when materializing parent/child chains to bound iteration
# in the presence of unexpected cycles (the create/update path also rejects
# them, but defense in depth is cheap).
_MAX_HIERARCHY_DEPTH = 16


async def expand_with_descendants(
    session: AsyncSession,
    seed_ids: list[uuid.UUID],
) -> list[uuid.UUID]:
    """
    @brief Return ``seed_ids`` plus all descendant subgroup IDs.

    BFS over ``parent_id`` edges. Used to translate "user is member of X"
    into "user has inherited access to X and every descendant of X" for
    parent → child cascade.
    """
    if not seed_ids:
        return []
    seen = set(seed_ids)
    frontier: list[uuid.UUID] = list(seed_ids)
    for _ in range(_MAX_HIERARCHY_DEPTH):
        if not frontier:
            break
        stmt = select(Subgroup.id).where(Subgroup.parent_id.in_(frontier))
        result = await session.execute(stmt)
        new_ids = [r[0] for r in result.all() if r[0] not in seen]
        seen.update(new_ids)
        frontier = new_ids
    return list(seen)


def visible_subgroup_ids_subq(user_id: uuid.UUID) -> Any:
    """
    @brief SQL subquery yielding subgroup IDs visible to ``user_id`` via
    direct membership or ancestor membership (parent → child cascade).

    Implemented as a recursive CTE: seed from the user's direct
    memberships, then walk down the ``parent_id`` edges to include every
    descendant.
    """
    seed = (
        select(SubgroupMember.subgroup_id.label("id"))
        .where(SubgroupMember.user_id == user_id)
        .cte("visible_subgroups", recursive=True)
    )
    child = aliased(Subgroup)
    seed = seed.union_all(
        select(child.id.label("id")).where(child.parent_id == seed.c.id),
    )
    return select(seed.c.id)


logger = structlog.get_logger(__name__)


class SubgroupRepository(BaseRepository[Subgroup]):
    """
    @brief Async repository for Subgroup CRUD and discovery queries.

    @param session Async SQLAlchemy session.
    """

    model = Subgroup

    async def get_slugs(
        self,
        ids: list[uuid.UUID],
        community_id: uuid.UUID,
    ) -> dict[uuid.UUID, str]:
        """
        @brief Fetch slugs for many subgroups in one community-scoped query.

        @param ids Subgroup IDs (duplicates allowed).
        @param community_id Community scope.
        @return Mapping of subgroup ID to slug; unknown IDs are omitted.
        """
        if not ids:
            return {}
        stmt = select(Subgroup.id, Subgroup.slug).where(
            Subgroup.id.in_(set(ids)),
            Subgroup.community_id == community_id,
        )
        result = await self._session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def get_ancestor_ids(
        self,
        subgroup_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        """
        @brief Walk the ``parent_id`` chain upward from ``subgroup_id``.

        @return List of ancestor subgroup IDs, ordered nearest → root.
                Excludes ``subgroup_id`` itself.
        """
        ids: list[uuid.UUID] = []
        seen: set[uuid.UUID] = {subgroup_id}
        current = subgroup_id
        for _ in range(_MAX_HIERARCHY_DEPTH):
            stmt = select(Subgroup.parent_id).where(Subgroup.id == current)
            result = await self._session.execute(stmt)
            parent_id = result.scalar_one_or_none()
            if parent_id is None or parent_id in seen:
                break
            ids.append(parent_id)
            seen.add(parent_id)
            current = parent_id
        return ids

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
            # Public subgroups OR private subgroups the user has access to
            # via direct membership or ancestor-membership cascade.
            from sqlalchemy import or_

            stmt = stmt.where(
                or_(
                    Subgroup.is_private.is_(False),
                    Subgroup.id.in_(visible_subgroup_ids_subq(user_id)),
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
        parent_id: uuid.UUID | None = None,
        cover_media_id: uuid.UUID | None = None,
    ) -> Subgroup:
        """
        @brief Insert a new subgroup row.

        @param cover_media_id Optional cover media ID (already validated).
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
            parent_id=parent_id,
            cover_media_id=cover_media_id,
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

    async def hard_delete(self, subgroup: Subgroup) -> None:
        """
        @brief Permanently delete a subgroup row.

        Cascades take care of members, chat channels, prompts, and pinned
        rows; events / posts / galleries become orphaned to community
        scope (their ``subgroup_id`` is ``SET NULL``). Children groups
        also detach (``parent_id`` becomes NULL) rather than disappearing.
        """
        await self._session.delete(subgroup)
        await self._session.flush()

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

    async def get_media_by_id(
        self,
        media_id: uuid.UUID,
    ) -> Media | None:
        """
        @brief Fetch a media row by ID.

        @param media_id The media's UUID.
        @return The Media or None.
        """
        stmt = select(Media).where(Media.id == media_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_member(
        self,
        subgroup_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """
        @brief Check if a user is a member of a subgroup.

        @param subgroup_id Subgroup ID.
        @param user_id User ID.
        @return True if user is a member.
        """
        stmt = select(func.count(SubgroupMember.user_id)).where(
            SubgroupMember.subgroup_id == subgroup_id,
            SubgroupMember.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0) > 0


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

    async def list_my_roles(
        self,
        user_id: uuid.UUID,
    ) -> dict[uuid.UUID, str]:
        """
        @brief Map subgroup_id -> role for every direct membership of user_id.
        @return Dict keyed by subgroup_id with role value.
        """
        stmt = select(SubgroupMember.subgroup_id, SubgroupMember.role).where(
            SubgroupMember.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return {sid: role for sid, role in result.all()}

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
