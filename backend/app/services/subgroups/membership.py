"""
@file membership.py
@brief Membership operations — join, leave, list, role change, remove.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.core.i18n import _
from app.models.subgroup import SubgroupMember
from app.models.user import User
from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository
from app.services.subgroups.helpers import count_owners, is_admin, require_role


class SubgroupMembershipMixin:
    """
    @brief Mixin exposing membership operations.

    Expected attributes:
      - ``_subgroup_repo``, ``_member_repo``, ``_community_id``
      - ``_max_memberships`` — per-user cap for active memberships
    """

    _subgroup_repo: SubgroupRepository
    _member_repo: SubgroupMemberRepository
    _community_id: uuid.UUID
    _max_memberships: int

    async def get_subgroup(self, slug: str, user: User) -> Any:  # noqa: D401
        """@brief Implemented in :class:`SubgroupCrudMixin`."""
        raise NotImplementedError

    async def join_subgroup(self, slug: str, user: User) -> dict[str, Any]:
        """
        @brief Join a subgroup, honouring the join policy.

        - ``open`` — user is added as ``member`` immediately.
        - ``invite_only`` / ``admin_approval`` — returns ``status="pending"``.

        Enforces the per-user active membership cap (admins bypass).

        @param slug Subgroup slug.
        @param user Requesting user.
        @return Dict with ``status`` and optional ``role`` / ``policy``.
        @raises NotFoundError If subgroup missing.
        @raises ConflictError If already a member or over the limit.
        @raises AuthorizationError If subgroup archived.
        """
        subgroup = await self.get_subgroup(slug, user)

        if subgroup.archived_at is not None:
            raise AuthorizationError(message=_("This subgroup is archived"))

        existing = await self._member_repo.get_membership(subgroup.id, user.id)
        if existing is not None:
            raise ConflictError(message=_("You are already a member of this subgroup"))

        if not is_admin(user):
            current = await self._member_repo.count_for_user(user.id, self._community_id)
            if current >= self._max_memberships:
                raise ConflictError(
                    message=_("You have reached the maximum number of subgroup memberships"),
                )

        if subgroup.join_policy == "open":
            await self._member_repo.add_member(
                community_id=self._community_id,
                subgroup_id=subgroup.id,
                user_id=user.id,
                role="member",
            )
            return {"status": "joined", "role": "member"}

        return {"status": "pending", "policy": subgroup.join_policy}

    async def leave_subgroup(self, slug: str, user: User) -> None:
        """
        @brief Leave a subgroup.

        The last remaining owner cannot leave unless they are an admin.

        @param slug Subgroup slug.
        @param user Requesting user.
        @raises NotFoundError If not a member.
        @raises ConflictError If user is the sole owner.
        """
        subgroup = await self.get_subgroup(slug, user)
        membership = await self._member_repo.get_membership(subgroup.id, user.id)
        if membership is None:
            raise NotFoundError(message=_("You are not a member of this subgroup"))

        if membership.role == "owner" and not is_admin(user):
            owner_count = await count_owners(self._member_repo, subgroup.id)
            if owner_count <= 1:
                raise ConflictError(
                    message=_("Transfer ownership before leaving the subgroup"),
                )

        await self._member_repo.remove_member(subgroup.id, user.id)

    async def list_members(
        self,
        slug: str,
        user: User,
    ) -> list[tuple[SubgroupMember, User]]:
        """
        @brief List members of a subgroup.

        @param slug Subgroup slug.
        @param user Requesting user (visibility-checked).
        @return List of (SubgroupMember, User) tuples.
        """
        subgroup = await self.get_subgroup(slug, user)
        return await self._member_repo.list_members(subgroup.id)

    async def change_role(
        self,
        slug: str,
        target_user_id: uuid.UUID,
        role: str,
        user: User,
    ) -> SubgroupMember:
        """
        @brief Change a member's role (owner or admin only).

        @param slug Subgroup slug.
        @param target_user_id User whose role should change.
        @param role New role value.
        @param user Acting user.
        @return The updated SubgroupMember.
        @raises NotFoundError If target membership does not exist.
        @raises AuthorizationError If user lacks permission.
        """
        subgroup = await self.get_subgroup(slug, user)
        await require_role(self._member_repo, subgroup, user, {"owner"})

        membership = await self._member_repo.get_membership(subgroup.id, target_user_id)
        if membership is None:
            raise NotFoundError(message=_("Membership not found"))

        return await self._member_repo.update_role(membership, role)

    async def remove_member(
        self,
        slug: str,
        target_user_id: uuid.UUID,
        user: User,
    ) -> None:
        """
        @brief Remove a member (owner/moderator/admin only).

        @param slug Subgroup slug.
        @param target_user_id User to remove.
        @param user Acting user.
        @raises NotFoundError If target membership does not exist.
        @raises AuthorizationError If user lacks permission.
        """
        subgroup = await self.get_subgroup(slug, user)
        await require_role(self._member_repo, subgroup, user, {"owner", "moderator"})

        membership = await self._member_repo.get_membership(subgroup.id, target_user_id)
        if membership is None:
            raise NotFoundError(message=_("Membership not found"))

        if membership.role == "owner" and not is_admin(user):
            raise AuthorizationError(message=_("Cannot remove the owner of a subgroup"))

        await self._member_repo.remove_member(subgroup.id, target_user_id)
