"""
@file crud.py
@brief Subgroup CRUD operations — create, read, list, update, archive.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.core.i18n import _
from app.models.subgroup import ChatChannel, Subgroup
from app.models.user import User
from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository
from app.services.subgroups.helpers import is_admin, require_role

logger = structlog.get_logger(__name__)


class SubgroupCrudMixin:
    """
    @brief Mixin exposing subgroup CRUD operations.

    Expected attributes on the host class:
      - ``_subgroup_repo`` — :class:`SubgroupRepository`
      - ``_member_repo`` — :class:`SubgroupMemberRepository`
      - ``_community_id`` — community UUID
    """

    _subgroup_repo: SubgroupRepository
    _member_repo: SubgroupMemberRepository
    _community_id: uuid.UUID

    async def _validate_parent(
        self,
        parent_id: uuid.UUID | None,
        *,
        self_id: uuid.UUID | None = None,
    ) -> None:
        """
        @brief Validate that ``parent_id`` is a valid parent subgroup.

        Ensures the parent exists in the same community and is not the
        subgroup itself nor an ancestor of itself (cycle check).

        @param parent_id Candidate parent subgroup UUID (None is fine).
        @param self_id Subgroup being created/updated, for cycle check.
        @raises NotFoundError If parent not found in this community.
        @raises ConflictError If parent_id == self_id or creates a cycle.
        """
        if parent_id is None:
            return

        if self_id is not None and parent_id == self_id:
            raise ConflictError(message=_("A group cannot be its own parent"))

        parent = await self._subgroup_repo.get_by_id(parent_id)
        if parent is None or parent.community_id != self._community_id:
            raise NotFoundError(message=_("Parent group not found"))

        # Walk up the chain, breaking on root or cycle into self.
        seen: set[uuid.UUID] = {parent_id}
        cursor = parent
        while cursor.parent_id is not None:
            if self_id is not None and cursor.parent_id == self_id:
                raise ConflictError(message=_("Parent assignment would create a cycle"))
            if cursor.parent_id in seen:
                break
            seen.add(cursor.parent_id)
            ancestor = await self._subgroup_repo.get_by_id(cursor.parent_id)
            if ancestor is None:
                break
            cursor = ancestor

    async def create_subgroup(
        self,
        user: User,
        *,
        name: str,
        slug: str,
        description: str | None = None,
        avatar_url: str | None = None,
        is_private: bool = False,
        join_policy: str = "open",
        parent_id: uuid.UUID | None = None,
        cover_media_id: uuid.UUID | None = None,
        initial_owner_id: uuid.UUID | None = None,
    ) -> tuple[Subgroup, ChatChannel]:
        """
        @brief Create a new subgroup.

        Enforces slug uniqueness, auto-adds the creator as ``owner`` (or moderator
        if ``initial_owner_id`` is set), and inserts the associated chat channel row.

        @param user The authenticated user creating the subgroup.
        @param name Subgroup display name.
        @param slug URL-safe unique identifier.
        @param description Optional description.
        @param avatar_url Optional avatar URL.
        @param is_private Hide from public discovery when true.
        @param join_policy One of ``open``/``invite_only``/``admin_approval``.
        @param cover_media_id Optional cover media ID (must be in same community).
        @param initial_owner_id Optional user ID to assign as owner; creator becomes moderator.
        @return Tuple of (Subgroup, ChatChannel).
        @raises ConflictError If a subgroup with this slug exists.
        @raises NotFoundError If cover_media_id or initial_owner_id invalid.
        """
        existing = await self._subgroup_repo.get_by_slug(slug, self._community_id)
        if existing is not None:
            raise ConflictError(message=_("A subgroup with this slug already exists"))

        await self._validate_parent(parent_id)

        # Validate cover_media_id if provided
        if cover_media_id is not None:
            media = await self._subgroup_repo.get_media_by_id(cover_media_id)
            if media is None or media.community_id != self._community_id:
                raise NotFoundError(message=_("Media not found or not in this community"))

        # Validate initial_owner_id if provided
        if initial_owner_id is not None and initial_owner_id != user.id:
            owner = await self._get_user_by_id(initial_owner_id)
            if owner is None or owner.community_id != self._community_id:
                raise NotFoundError(message=_("User not found or not in this community"))

        subgroup = await self._subgroup_repo.create_subgroup(
            community_id=self._community_id,
            name=name,
            slug=slug,
            description=description,
            avatar_url=avatar_url,
            is_private=is_private,
            join_policy=join_policy,
            created_by=user.id,
            parent_id=parent_id,
            cover_media_id=cover_media_id,
        )

        # Add members: if initial_owner_id, add target as owner and creator as moderator
        if initial_owner_id is not None and initial_owner_id != user.id:
            await self._member_repo.add_member(
                community_id=self._community_id,
                subgroup_id=subgroup.id,
                user_id=initial_owner_id,
                role="owner",
            )
            await self._member_repo.add_member(
                community_id=self._community_id,
                subgroup_id=subgroup.id,
                user_id=user.id,
                role="moderator",
            )
        else:
            # Creator is owner (default)
            await self._member_repo.add_member(
                community_id=self._community_id,
                subgroup_id=subgroup.id,
                user_id=user.id,
                role="owner",
            )

        channel = await self._subgroup_repo.create_chat_channel(
            community_id=self._community_id,
            subgroup_id=subgroup.id,
            name=name,
        )

        logger.info(
            "subgroup_created",
            subgroup_id=str(subgroup.id),
            slug=slug,
            created_by=str(user.id),
        )
        return subgroup, channel

    async def _get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        """
        @brief Fetch a user by ID, filtered by community.

        @param user_id User UUID.
        @return The User or None.
        """
        from sqlalchemy import select

        stmt = select(User).where(
            User.id == user_id,
            User.community_id == self._community_id,
            User.deleted_at.is_(None),
        )
        result = await self._subgroup_repo._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_subgroup(self, slug: str, user: User) -> Subgroup:
        """
        @brief Fetch a subgroup by slug, enforcing visibility rules.

        Private subgroups are visible only to members or admins.

        @param slug Subgroup slug.
        @param user Requesting user.
        @return The Subgroup ORM instance.
        @raises NotFoundError If not found or not visible.
        """
        subgroup = await self._subgroup_repo.get_by_slug(slug, self._community_id)
        if subgroup is None:
            raise NotFoundError(message=_("Subgroup not found"))

        if subgroup.is_private and not is_admin(user):
            membership = await self._member_repo.get_membership(subgroup.id, user.id)
            if membership is None:
                raise NotFoundError(message=_("Subgroup not found"))

        return subgroup

    async def list_subgroups(self, user: User) -> list[Subgroup]:
        """
        @brief List subgroups visible to the requesting user.

        @param user Requesting user.
        @return List of Subgroup rows.
        """
        return await self._subgroup_repo.list_visible_for_user(
            self._community_id,
            user.id,
            is_admin=is_admin(user),
        )

    async def update_subgroup(
        self,
        slug: str,
        user: User,
        updates: dict[str, Any],
    ) -> Subgroup:
        """
        @brief Update subgroup fields (owner/moderator/admin only).

        @param slug Subgroup slug.
        @param user Acting user.
        @param updates Dict of field updates.
        @return The updated Subgroup.
        @raises NotFoundError If subgroup not found or cover_media_id is
            from a different community.
        @raises AuthorizationError If user lacks permission or subgroup
            is archived.
        """
        subgroup = await self.get_subgroup(slug, user)
        await require_role(
            self._member_repo, self._subgroup_repo, subgroup, user, {"owner", "moderator"}
        )

        if subgroup.archived_at is not None and not is_admin(user):
            raise AuthorizationError(message=_("Archived subgroups are read-only"))

        if "parent_id" in updates:
            await self._validate_parent(updates["parent_id"], self_id=subgroup.id)

        if "cover_media_id" in updates and updates["cover_media_id"] is not None:
            media = await self._subgroup_repo.get_media_by_id(updates["cover_media_id"])
            if media is None or media.community_id != self._community_id:
                raise NotFoundError(message=_("Media not found or not in this community"))

        return await self._subgroup_repo.update_fields(subgroup, updates)

    async def hard_delete_subgroup(self, slug: str, user: User) -> None:
        """
        @brief Permanently delete a subgroup (community admin only).

        Owners can only archive; permanent deletion is gated behind the
        admin role to keep blast radius contained. Cascades and SET NULL
        FKs handle dependent rows — see :meth:`SubgroupRepository.hard_delete`.

        @param slug Subgroup slug.
        @param user Requesting user (must be community admin).
        @raises NotFoundError If subgroup not found.
        @raises AuthorizationError If user is not an admin.
        """
        if not is_admin(user):
            raise AuthorizationError(
                message=_("Only administrators can permanently delete a group"),
            )
        subgroup = await self.get_subgroup(slug, user)
        await self._subgroup_repo.hard_delete(subgroup)

    async def archive_subgroup(self, slug: str, user: User) -> Subgroup:
        """
        @brief Archive a subgroup (owner or admin only).

        @param slug Subgroup slug.
        @param user Requesting user.
        @return The archived Subgroup.
        @raises NotFoundError If subgroup not found.
        @raises AuthorizationError If user is not owner or admin.
        """
        subgroup = await self.get_subgroup(slug, user)
        await require_role(self._member_repo, self._subgroup_repo, subgroup, user, {"owner"})
        return await self._subgroup_repo.archive(subgroup)
