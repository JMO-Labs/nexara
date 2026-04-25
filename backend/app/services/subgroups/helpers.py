"""
@file helpers.py
@brief Shared helpers for the subgroup service modules.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.core.exceptions import AuthorizationError
from app.core.i18n import _
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.subgroup_repo import SubgroupMemberRepository


def is_admin(user: User) -> bool:
    """@brief Return True when the user has the community admin role."""
    return getattr(user, "role", None) == "admin"


async def require_role(
    member_repo: SubgroupMemberRepository,
    subgroup: Subgroup,
    user: User,
    allowed_roles: set[str],
) -> SubgroupMember | None:
    """
    @brief Raise :class:`AuthorizationError` unless the user has one of
    the allowed subgroup roles (or is a community admin).

    @param member_repo Membership repository.
    @param subgroup Subgroup in question.
    @param user Acting user.
    @param allowed_roles Set of allowed role strings.
    @return The membership row, or None for admins.
    """
    if is_admin(user):
        return None
    membership = await member_repo.get_membership(subgroup.id, user.id)
    if membership is None or membership.role not in allowed_roles:
        raise AuthorizationError(
            message=_("You do not have permission for this action"),
        )
    return membership


async def count_owners(
    member_repo: SubgroupMemberRepository,
    subgroup_id: uuid.UUID,
) -> int:
    """@brief Count owners in a subgroup."""
    session = member_repo._session
    stmt = select(func.count(SubgroupMember.user_id)).where(
        SubgroupMember.subgroup_id == subgroup_id,
        SubgroupMember.role == "owner",
    )
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)
