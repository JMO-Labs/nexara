"""
@file age_service.py
@brief Age groups: effective group derivation, admin control and member suggestions.

Admin-set group wins; otherwise the birthday decides (unless the community
requires approval for adults); otherwise "unknown" (treated as non-adult).
Suggestions never notify the subject; only admins are told.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Literal

from app.core.exceptions import AppError, NotFoundError
from app.core.i18n import _
from app.models.age_suggestion import AgeSuggestion
from app.repositories.age_repo import AgeRepository

AgeGroup = Literal["child", "teen", "adult", "unknown"]
GROUPS = ("child", "teen", "adult")


def _age(birthday: date) -> int:
    today = date.today()
    return today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))


def effective_age_group(user: Any, community: Any | None) -> AgeGroup:
    """
    @brief Resolve a user's age group.
    @param user Object with ``age_group`` and ``birthday``.
    @param community Object with ``adult_requires_approval`` (None = off).
    @return child/teen/adult, or unknown when undetermined.
    """
    group = getattr(user, "age_group", None)
    if group in GROUPS:
        return group  # type: ignore[no-any-return]
    b = user.birthday
    if not isinstance(b, date):
        return "unknown"
    age = _age(b)
    if age < 13:
        return "child"
    if age < 18:
        return "teen"
    if community is not None and community.adult_requires_approval is True:
        return "unknown"
    return "adult"


def is_adult(user: Any, community: Any | None) -> bool:
    """@brief Whether the user may see adult (NSFW) content."""
    return effective_age_group(user, community) == "adult"


class AgeService:
    """@brief Admin age-group management and member suggestions."""

    def __init__(
        self,
        repo: AgeRepository,
        community_id: uuid.UUID,
        actor_id: uuid.UUID,
        audit_repo: Any | None = None,
        notifier: Any | None = None,
        ip_address: str | None = None,
    ) -> None:
        self._repo = repo
        self._cid = community_id
        self._actor = actor_id
        self._audit = audit_repo
        self._notifier = notifier
        self._ip = ip_address

    async def _log(self, action: str, target_id: uuid.UUID, extra: dict[str, Any]) -> None:
        if self._audit is not None:
            await self._audit.append(
                actor_id=self._actor,
                action=action,
                target_type="user",
                target_id=target_id,
                extra_data=extra,
                ip_address=self._ip,
            )

    @staticmethod
    def _check_group(group: str | None) -> None:
        if group is not None and group not in GROUPS:
            raise AppError(
                code="INVALID_AGE_GROUP", message=_("Invalid age group"), status_code=400
            )

    async def _subject(self, subject_id: uuid.UUID) -> Any:
        user = await self._repo.get_user(self._cid, subject_id)
        if user is None:
            raise NotFoundError(_("User not found"))
        return user

    async def set_user_group(self, user_id: uuid.UUID, group: str | None) -> None:
        """@brief Admin sets (or clears) a user's age group."""
        self._check_group(group)
        user = await self._subject(user_id)
        await self._repo.set_user_group(user, group)
        await self._log("age_group.set", user_id, {"age_group": group})

    async def set_adult_requires_approval(self, value: bool) -> bool:
        """@brief Admin toggles approval mode."""
        await self._repo.set_adult_requires_approval(self._cid, value)
        return value

    async def settings(self) -> bool:
        """@brief Current approval-mode flag."""
        c = await self._repo.get_community(self._cid)
        return bool(c.adult_requires_approval) if c else False

    async def suggest(self, subject_id: uuid.UUID, group: str, note: str | None) -> AgeSuggestion:
        """@brief Member suggests a group for another member; admins are notified."""
        self._check_group(group)
        if group is None:
            raise AppError(
                code="INVALID_AGE_GROUP", message=_("Invalid age group"), status_code=400
            )
        if subject_id == self._actor:
            raise AppError(
                code="SELF_AGE_SUGGESTION",
                message=_("You cannot suggest your own age group"),
                status_code=400,
            )
        await self._subject(subject_id)
        if await self._repo.pending_exists(self._cid, subject_id, self._actor):
            raise AppError(
                code="AGE_SUGGESTION_EXISTS",
                message=_("You already have a pending suggestion for this member"),
                status_code=409,
            )
        row = await self._repo.create(self._cid, subject_id, self._actor, group, note)
        if self._notifier is not None:
            for admin_id in await self._repo.list_admin_ids(self._cid):
                if admin_id in (subject_id, self._actor):
                    continue  # subject is never notified
                await self._notifier.notify(
                    user_id=admin_id,
                    type="age_suggestion",
                    payload={
                        "message": _("A member suggested an age group for someone"),
                        "link": "/admin/age-groups",
                    },
                    actor_id=self._actor,
                )
        return row

    async def list_suggestions(self, status: str | None) -> list[AgeSuggestion]:
        """@brief Admin: suggestions filtered by status."""
        return await self._repo.list(self._cid, status)

    async def decide(self, suggestion_id: uuid.UUID, approve: bool) -> AgeSuggestion:
        """@brief Admin approves (sets the user's group) or rejects a pending suggestion."""
        row = await self._repo.get(self._cid, suggestion_id)
        if row is None:
            raise NotFoundError(_("Suggestion not found"))
        if row.status != "pending":
            raise AppError(
                code="SUGGESTION_DECIDED", message=_("Suggestion already decided"), status_code=409
            )
        status = "approved" if approve else "rejected"
        if approve:
            await self._repo.set_user_group(await self._subject(row.subject_id), row.age_group)
        await self._repo.decide(row, status, self._actor)
        await self._log(
            f"age_group.suggestion.{status}",
            row.subject_id,
            {"suggestion_id": str(row.id), "age_group": row.age_group},
        )
        return row
