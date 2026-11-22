"""
@file time_capsule_repo.py
@brief Data access for time capsules: viewer-scoped reads, recipient
       resolution, own-media / audience validation, atomic open-claim and
       the sealed-media check used by media serving.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import HouseholdMember
from app.models.media import Media
from app.models.moderation import UserBlock
from app.models.subgroup import SubgroupMember
from app.models.time_capsule import TimeCapsule, TimeCapsuleRecipient
from app.models.user import User
from app.repositories.household_repo import household_visible
from app.repositories.visibility_preds import my_subgroup_ids, not_blocked

R = TimeCapsuleRecipient


def _recipient_of(viewer_id: uuid.UUID, community_id: uuid.UUID) -> Any:
    """@brief Predicate: viewer is a recipient of ``TimeCapsule`` (row correlated)."""
    mine_hh = select(HouseholdMember.id).where(
        HouseholdMember.owner_id == viewer_id, HouseholdMember.deleted_at.is_(None)
    )
    match = or_(
        and_(R.kind == "user", R.target_id == viewer_id),
        R.kind == "community",
        and_(R.kind == "subgroup", R.target_id.in_(my_subgroup_ids(viewer_id))),
        and_(R.kind == "household", R.target_id.in_(mine_hh)),
    )
    return exists().where(R.capsule_id == TimeCapsule.id, match)


class TimeCapsuleRepository:
    """@brief Async repository for TimeCapsule / TimeCapsuleRecipient."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        community_id: uuid.UUID,
        author_id: uuid.UUID,
        *,
        title: str,
        body: str,
        media_ids: list[uuid.UUID],
        open_at: datetime,
        recipients: list[tuple[str, uuid.UUID]],
    ) -> TimeCapsule:
        """@brief Insert a capsule with its recipients and return it."""
        cap = TimeCapsule(
            community_id=community_id,
            author_id=author_id,
            title=title,
            body=body,
            media_ids=media_ids,
            open_at=open_at,
        )
        self._session.add(cap)
        await self._session.flush()
        for kind, target in set(recipients):
            self._session.add(R(capsule_id=cap.id, kind=kind, target_id=target))
        await self._session.flush()
        await self._session.refresh(cap)
        return cap

    async def get(self, capsule_id: uuid.UUID, community_id: uuid.UUID) -> TimeCapsule | None:
        """@brief Live capsule by id, or None."""
        stmt = select(TimeCapsule).where(
            TimeCapsule.id == capsule_id,
            TimeCapsule.community_id == community_id,
            TimeCapsule.deleted_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def is_recipient(
        self, capsule_id: uuid.UUID, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> bool:
        """@brief Whether the viewer is an audience member of the capsule."""
        stmt = select(TimeCapsule.id).where(
            TimeCapsule.id == capsule_id, _recipient_of(viewer_id, community_id)
        )
        return (await self._session.execute(stmt)).first() is not None

    async def list_for_viewer(
        self, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> list[TimeCapsule]:
        """@brief Capsules the viewer authored or receives (blocked authors hidden)."""
        stmt = (
            select(TimeCapsule)
            .where(
                TimeCapsule.community_id == community_id,
                TimeCapsule.deleted_at.is_(None),
                or_(
                    TimeCapsule.author_id == viewer_id,
                    and_(
                        _recipient_of(viewer_id, community_id),
                        not_blocked(TimeCapsule.author_id, viewer_id),
                    ),
                ),
            )
            .order_by(TimeCapsule.open_at)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def recipients(self, capsule_ids: list[uuid.UUID]) -> list[TimeCapsuleRecipient]:
        """@brief Recipient rows for the given capsules."""
        if not capsule_ids:
            return []
        stmt = select(R).where(R.capsule_id.in_(capsule_ids))
        return list((await self._session.execute(stmt)).scalars())

    async def visible_user_ids(
        self, ids: list[uuid.UUID], viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> set[uuid.UUID]:
        """@brief Subset of ``ids`` that are live, unblocked users of the community."""
        stmt = select(User.id).where(
            User.id.in_(ids),
            User.community_id == community_id,
            User.deleted_at.is_(None),
            not_blocked(User.id, viewer_id),
        )
        return set((await self._session.execute(stmt)).scalars())

    async def member_subgroup_ids(
        self, ids: list[uuid.UUID], viewer_id: uuid.UUID
    ) -> set[uuid.UUID]:
        """@brief Subset of ``ids`` the viewer belongs to."""
        stmt = select(SubgroupMember.subgroup_id).where(
            SubgroupMember.user_id == viewer_id, SubgroupMember.subgroup_id.in_(ids)
        )
        return set((await self._session.execute(stmt)).scalars())

    async def visible_household_ids(
        self, ids: list[uuid.UUID], viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> set[uuid.UUID]:
        """@brief Subset of ``ids`` that are household members the viewer may see."""
        stmt = select(HouseholdMember.id).where(
            HouseholdMember.id.in_(ids), household_visible(viewer_id, community_id)
        )
        return set((await self._session.execute(stmt)).scalars())

    async def own_media_count(
        self, ids: list[uuid.UUID], author_id: uuid.UUID, community_id: uuid.UUID
    ) -> int:
        """@brief How many of ``ids`` are the author's own media."""
        stmt = select(func.count(Media.id)).where(
            Media.id.in_(ids), Media.uploader_id == author_id, Media.community_id == community_id
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def author_names(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        """@brief Display names keyed by user id."""
        if not ids:
            return {}
        stmt = select(User.id, User.display_name).where(User.id.in_(ids))
        return {i: n for i, n in (await self._session.execute(stmt)).all()}

    async def claim_due(self, now: datetime) -> list[TimeCapsule]:
        """@brief Atomically stamp ``opened_at`` on due capsules and return them."""
        stmt = (
            update(TimeCapsule)
            .where(
                TimeCapsule.opened_at.is_(None),
                TimeCapsule.deleted_at.is_(None),
                TimeCapsule.open_at <= now,
            )
            .values(opened_at=now)
            .returning(TimeCapsule)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def resolve_user_ids(self, cap: TimeCapsule) -> set[uuid.UUID]:
        """@brief Users to notify: expanded audience minus author and blocked pairs."""
        rows = await self.recipients([cap.id])
        users: set[uuid.UUID] = set()
        for kind in ("user", "subgroup", "household", "community"):
            ids = [r.target_id for r in rows if r.kind == kind]
            if kind == "user":
                users.update(ids)
            elif kind == "subgroup" and ids:
                q = select(SubgroupMember.user_id).where(SubgroupMember.subgroup_id.in_(ids))
                users.update((await self._session.execute(q)).scalars())
            elif kind == "household" and ids:
                q = select(HouseholdMember.owner_id).where(
                    HouseholdMember.id.in_(ids), HouseholdMember.deleted_at.is_(None)
                )
                users.update((await self._session.execute(q)).scalars())
            elif kind == "community" and ids:
                q = select(User.id).where(User.community_id == cap.community_id)
                users.update((await self._session.execute(q)).scalars())
        users.discard(cap.author_id)
        if not users:
            return users
        blocked = select(UserBlock.blocked_id).where(UserBlock.blocker_id == cap.author_id)
        blockers = select(UserBlock.blocker_id).where(UserBlock.blocked_id == cap.author_id)
        stmt = select(User.id).where(
            User.id.in_(users),
            User.deleted_at.is_(None),
            User.is_active.is_(True),
            User.id.notin_(blocked),
            User.id.notin_(blockers),
        )
        return set((await self._session.execute(stmt)).scalars())

    async def delete(self, cap: TimeCapsule, now: datetime) -> None:
        """@brief Soft-delete a capsule."""
        cap.deleted_at = now
        await self._session.flush()

    async def is_sealed_media(
        self, media_id: uuid.UUID, community_id: uuid.UUID, viewer_id: uuid.UUID | None
    ) -> bool:
        """@brief Media belongs to a live, unopened capsule not authored by the viewer."""
        cond = [
            TimeCapsule.community_id == community_id,
            TimeCapsule.deleted_at.is_(None),
            TimeCapsule.opened_at.is_(None),
            TimeCapsule.media_ids.contains([media_id]),
        ]
        if viewer_id is not None:
            cond.append(TimeCapsule.author_id != viewer_id)
        stmt = select(TimeCapsule.id).where(*cond).limit(1)
        return (await self._session.execute(stmt)).first() is not None
