"""
@file memorial_service.py
@brief Memorials: a household member's passed-on date, and admin
       memorialize / restore of a member account. A memorialized account
       cannot sign in, is dropped from pickers, mentions and nudges, and
       shows as "Remembering <name>" on the calendar.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.core.features import require_feature
from app.core.i18n import _
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.community_repo import CommunityRepository
from app.repositories.household_repo import HouseholdRepository
from app.repositories.token_repo import TokenRepository
from app.repositories.user_repo import UserRepository
from app.services.relation_service import RelationService


def check_passed_on(passed_on: date | None, born: date | None) -> None:
    """
    @brief Validate a passed-on date.
    @throws ValidationError when in the future or before the birthday.
    """
    if passed_on is None:
        return
    if passed_on > datetime.now(UTC).date():
        raise ValidationError(message=_("The date can't be in the future"))
    if born is not None and passed_on < born:
        raise ValidationError(message=_("The date can't be before the birthday"))


class MemorialService:
    """@brief Business rules for memorials."""

    def __init__(
        self,
        household: HouseholdRepository,
        users: UserRepository,
        tokens: TokenRepository,
        audit: AuditRepository,
        communities: CommunityRepository,
        community_id: uuid.UUID,
        relations: RelationService | None = None,
    ) -> None:
        self._household = household
        self._users = users
        self._tokens = tokens
        self._audit = audit
        self._communities = communities
        self._cid = community_id
        self._relations = relations

    async def _require_feature(self) -> None:
        community = await self._communities.get(self._cid)
        if community is not None:
            require_feature(community, "memorials")

    async def _is_relative(self, actor: User, m: Any) -> bool:
        """@brief Actor is a confirmed relative of the member's owner."""
        if self._relations is None:
            return False
        return await self._relations.is_confirmed_relative(actor.id, m.owner_id)

    async def set_passed_on(self, member_id: uuid.UUID, actor: User, passed_on: date | None) -> Any:
        """
        @brief Set or clear a household member's passed-on date.
        @param member_id Household member id.
        @param actor Acting user; the owner, a confirmed relative of the owner, or an admin.
        @param passed_on Date, or None to clear.
        @throws AuthorizationError for anyone else; ValidationError for a bad date.
        """
        await self._require_feature()
        m = await self._household.get(member_id, self._cid)
        if m is None:
            raise NotFoundError(message=_("Not found"))
        if (
            m.owner_id != actor.id
            and actor.role != "admin"
            and not await self._is_relative(actor, m)
        ):
            raise AuthorizationError(
                message=_("Only the owner, a confirmed relative or an admin can do this")
            )
        check_passed_on(passed_on, m.birthday)
        return await self._household.update(m, {"passed_on": passed_on})

    async def _target(self, user_id: uuid.UUID, admin: User) -> User:
        if admin.role != "admin":
            raise AuthorizationError(message=_("Admin only"))
        target = await self._users.get_by_id(user_id, self._cid)
        if target is None:
            raise NotFoundError(message=_("User not found"))
        return target

    async def memorialize_user(
        self, user_id: uuid.UUID, admin: User, passed_on: date | None, ip: str | None = None
    ) -> None:
        """
        @brief Memorialize an account: lock it, revoke sessions, audit-log.
        @throws AuthorizationError when ``admin`` is not an admin.
        """
        await self._require_feature()
        target = await self._target(user_id, admin)
        check_passed_on(passed_on, target.birthday)
        await self._users.update(
            target,
            {"memorialized_at": datetime.now(UTC), "passed_on": passed_on, "is_active": False},
        )
        await self._tokens.revoke_all_for_user(target.id)
        await self._audit.append(
            actor_id=admin.id,
            action="admin.user.memorialized",
            target_type="user",
            target_id=target.id,
            extra_data={"passed_on": passed_on.isoformat() if passed_on else None},
            ip_address=ip,
        )

    async def unmemorialize_user(
        self, user_id: uuid.UUID, admin: User, ip: str | None = None
    ) -> None:
        """@brief Reverse :meth:`memorialize_user` (admin only)."""
        await self._require_feature()
        target = await self._target(user_id, admin)
        await self._users.update(
            target, {"memorialized_at": None, "passed_on": None, "is_active": True}
        )
        await self._audit.append(
            actor_id=admin.id,
            action="admin.user.unmemorialized",
            target_type="user",
            target_id=target.id,
            extra_data=None,
            ip_address=ip,
        )
