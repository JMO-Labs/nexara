"""
@file helpers.py
@brief Shared helpers for the subgroup service modules.

Includes the parent → child role-inheritance machinery used by
:func:`require_role`. A user's *effective* role in a subgroup is the
highest-ranked role they hold either directly on the subgroup or on any
ancestor (since cascade flows down).
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.core.exceptions import AuthorizationError
from app.core.i18n import _
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.subgroup_repo import (
    SubgroupMemberRepository,
    SubgroupRepository,
)

# Higher value = stronger role. ``None`` is treated as 0 (no membership).
_ROLE_RANK: dict[str, int] = {"member": 1, "moderator": 2, "owner": 3}


def is_admin(user: User) -> bool:
    """@brief Return True when the user has the community admin role."""
    return getattr(user, "role", None) == "admin"


def _role_rank(role: str | None) -> int:
    """@brief Numeric rank for a role string; unknown / None → 0."""
    if role is None:
        return 0
    return _ROLE_RANK.get(role, 0)


async def effective_membership(
    member_repo: SubgroupMemberRepository,
    subgroup_repo: SubgroupRepository,
    subgroup: Subgroup,
    user: User,
) -> SubgroupMember | None:
    """
    @brief Return the highest-ranked membership the user has on
    ``subgroup`` or any of its ancestors.

    Direct membership is checked first; if absent, walks ``parent_id``
    upward and picks the strongest ancestor membership. ``None`` means
    the user has no inherited or direct access.
    """
    direct = await member_repo.get_membership(subgroup.id, user.id)
    best = direct
    ancestor_ids = await subgroup_repo.get_ancestor_ids(subgroup.id)
    for aid in ancestor_ids:
        ancestor_m = await member_repo.get_membership(aid, user.id)
        if ancestor_m is None:
            continue
        if _role_rank(ancestor_m.role) > _role_rank(best.role if best else None):
            best = ancestor_m
    return best


async def require_role(
    member_repo: SubgroupMemberRepository,
    subgroup_repo: SubgroupRepository,
    subgroup: Subgroup,
    user: User,
    allowed_roles: set[str],
) -> SubgroupMember | None:
    """
    @brief Raise :class:`AuthorizationError` unless the user holds an
    allowed role — directly on ``subgroup`` or inherited from any
    ancestor. Community admins bypass.

    @param member_repo Membership repository.
    @param subgroup_repo Subgroup repository (used for ancestor walk).
    @param subgroup Subgroup in question.
    @param user Acting user.
    @param allowed_roles Set of allowed role strings.
    @return The effective membership row, or ``None`` for admins.
    """
    if is_admin(user):
        return None
    membership = await effective_membership(member_repo, subgroup_repo, subgroup, user)
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
