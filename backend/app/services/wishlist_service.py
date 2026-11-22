"""
@file wishlist_service.py
@brief Wishlists for anyone (members, household members/pets, groups, typed
       names or everyone): browse, create, edit, delete, and the detail view.
       Items and claims live in WishlistGiftService.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.core.i18n import _
from app.models.user import User
from app.models.wishlist import Wishlist, WishlistRecipient
from app.repositories.wishlist_item_repo import WishlistItemRepository
from app.repositories.wishlist_repo import WishlistRepository
from app.schemas.wishlist import (
    RecipientIn,
    RecipientOut,
    WishlistCreate,
    WishlistDetail,
    WishlistOut,
    WishlistUpdate,
)
from app.services.wishlist_view import Access, build_items, planned_cents

MAX_LISTS = 50
LIST_FIELDS = (
    "title",
    "occasion",
    "occasion_label",
    "event_date",
    "due_by",
    "note",
    "visibility",
    "currency",
    "budget_min_cents",
    "budget_max_cents",
    "event_budget_cents",
    "giver_cap_cents",
    "hide_claims",
    "registry_links",
)


def _for_everyone(recipients: list[dict[str, Any]]) -> bool:
    """@brief The list is for everyone (reunion, BBQ)."""
    return any(r["kind"] == "everyone" for r in recipients)


class WishlistService:
    """@brief Wishlist rules, scoped to one community."""

    def __init__(
        self, repo: WishlistRepository, items: WishlistItemRepository, community_id: uuid.UUID
    ) -> None:
        self._repo = repo
        self._items = items
        self._cid = community_id

    # -- helpers ---------------------------------------------------------------

    async def _recipients_out(
        self, rows: list[WishlistRecipient], viewer: User
    ) -> dict[uuid.UUID, list[RecipientOut]]:
        ids = {
            k: [r.ref_id for r in rows if r.kind == k and r.ref_id]
            for k in ("user", "household", "subgroup")
        }
        users = await self._repo.user_names(ids["user"], self._cid)
        homes = await self._repo.household_names(ids["household"], viewer.id, self._cid)
        groups = await self._repo.group_names(ids["subgroup"], self._cid)
        out: dict[uuid.UUID, list[RecipientOut]] = {}
        for r in rows:
            name, extra = r.name or "", None
            if r.kind == "everyone":
                name = _("Everyone")
            elif r.kind == "user" and r.ref_id in users:
                name = users[r.ref_id]
            elif r.kind == "household" and r.ref_id in homes:
                name, extra = homes[r.ref_id]
            elif r.kind == "subgroup" and r.ref_id in groups:
                name, extra = groups[r.ref_id]
            if not name:
                continue  # deleted or hidden from this viewer
            out.setdefault(r.wishlist_id, []).append(
                RecipientOut(kind=r.kind, ref_id=r.ref_id, name=name, extra=extra)
            )
        return out

    async def _summaries(self, rows: list[tuple[Wishlist, int]], viewer: User) -> list[WishlistOut]:
        recips = await self._recipients_out(
            await self._repo.recipients([w.id for w, _n in rows]), viewer
        )
        owners = await self._repo.user_names(list({w.owner_id for w, _n in rows}), self._cid)
        out = []
        for w, n in rows:
            rs = recips.get(w.id, [])
            access = Access(
                is_owner=w.owner_id == viewer.id,
                is_recipient=any(r.kind == "user" and r.ref_id == viewer.id for r in rs),
            )
            out.append(
                WishlistOut(
                    id=w.id,
                    owner_id=w.owner_id,
                    owner_name=owners.get(w.owner_id, ""),
                    **{f: getattr(w, f) for f in LIST_FIELDS},
                    recipients=rs,
                    item_count=n,
                    is_owner=access.is_owner,
                    can_edit_items=access.can_edit_items,
                    sees_claims=access.sees_claims(w),
                )
            )
        return out

    async def visible(self, wishlist_id: uuid.UUID, viewer: User) -> Wishlist:
        """@brief A list the viewer may see, else 404."""
        row = await self._repo.get_visible(wishlist_id, viewer.id, self._cid)
        if row is None:
            raise NotFoundError(message=_("Wishlist not found"))
        return row

    async def access(self, w: Wishlist, viewer: User) -> Access:
        """@brief The viewer's rights on ``w``."""
        return Access(
            is_owner=w.owner_id == viewer.id,
            is_recipient=await self._repo.is_recipient(w.id, viewer.id),
        )

    async def _owned(self, wishlist_id: uuid.UUID, viewer: User) -> Wishlist:
        row = await self.visible(wishlist_id, viewer)
        if row.owner_id != viewer.id:
            raise AuthorizationError(message=_("Only the list's creator can change it"))
        return row

    async def _clean_recipients(
        self, items: list[RecipientIn], actor: User
    ) -> list[dict[str, Any]]:
        """@brief Validate recipients; "everyone" replaces all others."""
        if any(r.kind == "everyone" for r in items):
            return [{"kind": "everyone"}]
        ids = {
            k: [r.ref_id for r in items if r.kind == k and r.ref_id]
            for k in ("user", "household", "subgroup")
        }
        users = await self._repo.user_names(ids["user"], self._cid)
        homes = await self._repo.household_names(ids["household"], actor.id, self._cid)
        groups = await self._repo.my_group_ids(actor.id, ids["subgroup"])
        seen: set[tuple[str, Any]] = set()
        out: list[dict[str, Any]] = []
        for r in items:
            ok = {
                "user": r.ref_id in users,
                "household": r.ref_id in homes,
                "subgroup": r.ref_id in groups,
                "name": True,
            }[r.kind]
            if not ok:
                raise NotFoundError(message=_("One of the recipients wasn't found"))
            key = (r.kind, r.ref_id or (r.name or "").lower())
            if key not in seen:
                seen.add(key)
                out.append(
                    {
                        "kind": r.kind,
                        "ref_id": r.ref_id,
                        "name": r.name if r.kind == "name" else None,
                    }
                )
        return out

    # -- reads -----------------------------------------------------------------

    async def list(
        self,
        viewer: User,
        person_id: uuid.UUID | None = None,
        household_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
    ) -> list[WishlistOut]:
        """@brief Lists the viewer may see; filter by person, household member or creator."""
        rows = await self._repo.visible(
            viewer.id, self._cid, person_id=person_id, household_id=household_id, owner_id=owner_id
        )
        return await self._summaries(rows, viewer)

    async def get(self, wishlist_id: uuid.UUID, viewer: User) -> WishlistDetail:
        """@brief A list with items; claims only for viewers allowed to see them."""
        w = await self.visible(wishlist_id, viewer)
        items = await self._items.items(w.id)
        (summary,) = await self._summaries([(w, len(items))], viewer)
        claims = await self._items.claims([i.id for i in items])
        previews = await self._items.previews([i.preview_id for i in items if i.preview_id])
        views, mine = build_items(items, claims, previews, viewer.id, summary.sees_claims)
        return WishlistDetail(
            **summary.model_dump(),
            items=views,
            planned_cents=planned_cents(items) if summary.can_edit_items else None,
            my_total_cents=mine,
        )

    # -- writes ----------------------------------------------------------------

    async def create(self, body: WishlistCreate, owner: User) -> WishlistDetail:
        """@brief New list; with no recipients it's for the creator."""
        recipients = await self._clean_recipients(
            body.recipients or [RecipientIn(kind="user", ref_id=owner.id)], owner
        )
        if len(await self._repo.visible(owner.id, self._cid, owner_id=owner.id)) >= MAX_LISTS:
            raise ValidationError(message=_("You have reached the wishlist limit"))
        values = body.model_dump(exclude={"recipients"}, exclude_none=True)
        values["registry_links"] = [r.model_dump() for r in body.registry_links or []]
        if _for_everyone(recipients):
            values["visibility"] = "community"
        w = await self._repo.create(community_id=self._cid, owner_id=owner.id, **values)
        await self._repo.replace_recipients(w, recipients)
        return await self.get(w.id, owner)

    async def update(
        self, wishlist_id: uuid.UUID, body: WishlistUpdate, owner: User
    ) -> WishlistDetail:
        """@brief Edit list settings and recipients (creator only)."""
        w = await self._owned(wishlist_id, owner)
        values: dict[str, Any] = body.model_dump(exclude_unset=True, exclude={"recipients"})
        for k in ("title", "occasion", "visibility", "currency", "hide_claims"):
            if values.get(k) is None:
                values.pop(k, None)
        if "registry_links" in values:
            values["registry_links"] = [r.model_dump() for r in body.registry_links or []]
        recipients = (
            await self._clean_recipients(body.recipients, owner)
            if body.recipients is not None
            else [{"kind": r.kind} for r in await self._repo.recipients([w.id])]
        )
        if _for_everyone(recipients):
            values["visibility"] = "community"  # a list for everyone is seen by everyone
        if values:
            await self._repo.update(w, values)
        if body.recipients is not None:
            await self._repo.replace_recipients(w, recipients)
        return await self.get(w.id, owner)

    async def delete(self, wishlist_id: uuid.UUID, owner: User) -> None:
        """@brief Remove a list (creator only)."""
        await self._repo.soft_delete(await self._owned(wishlist_id, owner))
