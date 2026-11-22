"""
@file household_service.py
@brief Household members and pets: owner-managed CRUD, privacy-filtered
       views and upcoming birthdays / gotcha days.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from app.core.exceptions import NotFoundError, ValidationError
from app.core.i18n import _
from app.models.household import HouseholdMember
from app.models.user import User
from app.repositories.household_repo import HouseholdRepository
from app.schemas.household import HouseholdCreate, HouseholdUpdate
from app.services.home_people_service import birthday_in_days
from app.services.household_handles import unique_handle

PET_ONLY = ("species", "breed", "gotcha_day", "likes", "dislikes", "care_card")
MAX_PER_OWNER = 30


class HouseholdService:
    """@brief Business rules for household members."""

    def __init__(self, repo: HouseholdRepository, community_id: uuid.UUID) -> None:
        self._repo = repo
        self._community_id = community_id

    async def view(self, m: HouseholdMember, viewer: User) -> dict[str, Any]:
        """@brief Response dict; hides birth year and care card as configured."""
        mine = m.owner_id == viewer.id
        bday = None
        if m.birthday:
            bday = (
                m.birthday.isoformat()
                if mine or m.show_birth_year
                else f"--{m.birthday.month:02d}-{m.birthday.day:02d}"
            )
        care = m.care_card if (mine or await self._repo.care_visible(m, viewer.id)) else None
        return {
            "id": m.id,
            "owner_id": m.owner_id,
            "kind": m.kind,
            "name": m.name,
            "handle": m.handle,
            "relation": m.relation,
            "birthday": bday,
            "show_birth_year": m.show_birth_year,
            "photo_media_id": m.photo_media_id,
            "visibility": m.visibility,
            "bio": m.bio,
            "species": m.species,
            "breed": m.breed,
            "gotcha_day": m.gotcha_day,
            "passed_on": m.passed_on,
            "likes": m.likes or [],
            "dislikes": m.dislikes or [],
            "care_card": care,
            "care_visibility": m.care_visibility,
            "can_edit": mine,
        }

    async def _views(self, rows: list[HouseholdMember], viewer: User) -> list[dict[str, Any]]:
        return [await self.view(m, viewer) for m in rows]

    async def list_for_owner(self, owner_id: uuid.UUID, viewer: User) -> list[dict[str, Any]]:
        """@brief An owner's members the viewer may see."""
        rows = await self._repo.visible(viewer.id, self._community_id, owner_id=owner_id)
        return await self._views(rows, viewer)

    async def list_visible(self, viewer: User) -> list[dict[str, Any]]:
        """@brief Every member the viewer may see (tag picker)."""
        return await self._views(await self._repo.visible(viewer.id, self._community_id), viewer)

    async def _get(self, member_id: uuid.UUID, viewer: User) -> HouseholdMember:
        m = await self._repo.get_visible(member_id, viewer.id, self._community_id)
        if m is None:
            raise NotFoundError(message=_("Not found"))
        return m

    async def get(self, member_id: uuid.UUID, viewer: User) -> dict[str, Any]:
        """@raises NotFoundError when hidden or missing."""
        return await self.view(await self._get(member_id, viewer), viewer)

    async def _owned(self, member_id: uuid.UUID, user: User) -> HouseholdMember:
        m = await self._get(member_id, user)
        if m.owner_id != user.id:
            raise NotFoundError(message=_("Not found"))
        return m

    async def _clean(self, data: HouseholdUpdate, kind: str) -> dict[str, Any]:
        fields = data.model_dump(exclude_unset=True, exclude={"kind"})
        if kind != "pet":
            for f in PET_ONLY:
                fields.pop(f, None)
        for k in ("relation", "bio", "species", "breed", "care_card"):
            if k in fields and isinstance(fields[k], str):
                fields[k] = fields[k].strip() or None
        for k in ("show_birth_year", "visibility", "care_visibility", "likes", "dislikes"):
            if k in fields and fields[k] is None:
                fields.pop(k)
        if fields.get("photo_media_id") and not await self._repo.media_in_community(
            fields["photo_media_id"], self._community_id
        ):
            raise ValidationError(message=_("Photo not found"))
        return fields

    async def create(self, user: User, data: HouseholdCreate) -> dict[str, Any]:
        """@brief Add a member owned by ``user``."""
        mine = await self._repo.visible(user.id, self._community_id, owner_id=user.id)
        if len(mine) >= MAX_PER_OWNER:
            raise ValidationError(message=_("Household is full"))
        fields = await self._clean(data, data.kind)
        fields["name"] = data.name.strip()
        fields["handle"] = await unique_handle(
            fields["name"], data.kind, lambda h: self._repo.handle_taken(self._community_id, h)
        )
        m = await self._repo.create(
            community_id=self._community_id, owner_id=user.id, kind=data.kind, **fields
        )
        return await self.view(m, user)

    async def update(
        self, member_id: uuid.UUID, user: User, data: HouseholdUpdate
    ) -> dict[str, Any]:
        """@brief Owner edits a member."""
        m = await self._owned(member_id, user)
        fields = await self._clean(data, m.kind)
        if "name" in fields:
            if not (fields["name"] or "").strip():
                raise ValidationError(message=_("Name is required"))
            fields["name"] = fields["name"].strip()
        return await self.view(await self._repo.update(m, fields), user)

    async def delete(self, member_id: uuid.UUID, user: User) -> None:
        """@brief Owner removes a member (and their tags)."""
        await self._repo.soft_delete(await self._owned(member_id, user))

    async def upcoming(self, viewer: User, today: date) -> list[dict[str, Any]]:
        """@brief Visible birthdays and gotcha days in the next 14 days, soonest first."""
        out: list[dict[str, Any]] = []
        for m in await self._repo.visible(viewer.id, self._community_id):
            if m.passed_on is not None:
                continue  # remembered on the calendar, not celebrated
            for occasion, day in (("birthday", m.birthday), ("gotcha_day", m.gotcha_day)):
                n = birthday_in_days(day, today)
                if n is not None:
                    out.append(
                        {"member": await self.view(m, viewer), "occasion": occasion, "in_days": n}
                    )
        return sorted(out, key=lambda c: c["in_days"])
