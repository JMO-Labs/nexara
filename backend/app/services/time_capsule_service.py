"""
@file time_capsule_service.py
@brief Sealed time capsules: create, list, get (seal-aware), delete and the
       scheduled open that notifies recipients exactly once.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.features import require_feature
from app.core.i18n import _
from app.models.time_capsule import TimeCapsule
from app.repositories.community_repo import CommunityRepository
from app.repositories.time_capsule_repo import TimeCapsuleRepository
from app.schemas.time_capsule import (
    CapsuleAuthor,
    CapsuleCreate,
    CapsuleOpen,
    CapsuleSealed,
)
from app.services.notification_service import NotificationService

MIN_LEAD = timedelta(hours=24)
MAX_LEAD = timedelta(days=365 * 50)
_PLURAL = {"user": "people", "subgroup": "groups", "household": "household members"}


def _invalid(message: str) -> AppError:
    return AppError("VALIDATION_ERROR", message, 422)


class TimeCapsuleService:
    """@brief Business rules for time capsules."""

    def __init__(
        self,
        repo: TimeCapsuleRepository,
        community_repo: CommunityRepository,
        notifications: NotificationService,
        community_id: uuid.UUID,
    ) -> None:
        self._repo = repo
        self._communities = community_repo
        self._notify = notifications
        self._community_id = community_id

    async def _require_feature(self) -> None:
        community = await self._communities.get(self._community_id)
        if community is not None:
            require_feature(community, "time_capsules")

    async def _validate_recipients(
        self, body: CapsuleCreate, author_id: uuid.UUID
    ) -> list[tuple[str, uuid.UUID]]:
        """@brief Normalise recipients and check the author may address each."""
        out: list[tuple[str, uuid.UUID]] = []
        by_kind: dict[str, set[uuid.UUID]] = {}
        for r in body.recipients:
            if r.kind == "community":
                out.append(("community", self._community_id))
                continue
            if r.target_id is None:
                raise _invalid(_("Recipient is missing a target"))
            by_kind.setdefault(r.kind, set()).add(r.target_id)
        checks: dict[str, Any] = {
            "user": lambda ids: self._repo.visible_user_ids(ids, author_id, self._community_id),
            "subgroup": lambda ids: self._repo.member_subgroup_ids(ids, author_id),
            "household": lambda ids: self._repo.visible_household_ids(
                ids, author_id, self._community_id
            ),
        }
        for kind, ids in by_kind.items():
            ok = await checks[kind](list(ids))
            if ids - ok:
                raise _invalid(_("You cannot address one of the recipients"))
            out.extend((kind, i) for i in ids)
        return out

    async def create(self, author_id: uuid.UUID, body: CapsuleCreate) -> CapsuleOpen:
        """
        @brief Seal a new capsule.
        @raises AppError 422 on bad date, recipients or media.
        """
        await self._require_feature()
        now = datetime.now(UTC)
        open_at = body.open_at if body.open_at.tzinfo else body.open_at.replace(tzinfo=UTC)
        if open_at < now + MIN_LEAD:
            raise _invalid(_("Open date must be at least 24 hours from now"))
        if open_at > now + MAX_LEAD:
            raise _invalid(_("Open date must be within 50 years"))
        recipients = await self._validate_recipients(body, author_id)
        media = list(dict.fromkeys(body.media_ids))
        if media and await self._repo.own_media_count(media, author_id, self._community_id) != len(
            media
        ):
            raise _invalid(_("You can only attach your own media"))
        cap = await self._repo.create(
            self._community_id,
            author_id,
            title=body.title.strip(),
            body=body.body,
            media_ids=media,
            open_at=open_at,
            recipients=recipients,
        )
        return (await self._build([cap], full=True))[0]  # type: ignore[return-value]

    async def _build(
        self, caps: list[TimeCapsule], *, full: bool
    ) -> list[CapsuleSealed | CapsuleOpen]:
        names = await self._repo.author_names(list({c.author_id for c in caps}))
        bots = await self._repo.bot_ids(list({c.author_id for c in caps}))
        rows = await self._repo.recipients([c.id for c in caps])
        out: list[CapsuleSealed | CapsuleOpen] = []
        for c in caps:
            kinds = [r.kind for r in rows if r.capsule_id == c.id]
            head: dict[str, Any] = {
                "id": c.id,
                "title": c.title,
                "author": CapsuleAuthor(
                    id=c.author_id,
                    display_name=names.get(c.author_id, ""),
                    is_bot=c.author_id in bots,
                ),
                "open_at": c.open_at,
                "recipients_summary": _summary(kinds),
            }
            if full:
                out.append(
                    CapsuleOpen(**head, body=c.body, media=list(c.media_ids), opened_at=c.opened_at)
                )
            else:
                out.append(CapsuleSealed(**head))
        return out

    async def list_for_viewer(self, viewer_id: uuid.UUID) -> dict[str, list[Any]]:
        """@return ``{"sealed", "opened", "mine"}`` lists for the viewer."""
        await self._require_feature()
        caps = await self._repo.list_for_viewer(viewer_id, self._community_id)
        mine = [c for c in caps if c.author_id == viewer_id]
        theirs = [c for c in caps if c.author_id != viewer_id]
        sealed = [c for c in theirs if c.opened_at is None]
        opened = [c for c in theirs if c.opened_at is not None]
        return {
            "sealed": await self._build(sealed, full=False),
            "opened": await self._build(opened, full=True),
            "mine": await self._build(mine, full=True),
        }

    async def get(self, capsule_id: uuid.UUID, viewer_id: uuid.UUID) -> CapsuleSealed | CapsuleOpen:
        """
        @brief Fetch one capsule; full content only if opened or viewer is author.
        @raises NotFoundError for non-recipients and blocked authors.
        """
        await self._require_feature()
        cap = await self._repo.get(capsule_id, self._community_id)
        if cap is None:
            raise NotFoundError(_("Capsule not found"))
        if cap.author_id != viewer_id:
            visible = await self._repo.visible_user_ids(
                [cap.author_id], viewer_id, self._community_id
            )
            if cap.author_id not in visible or not await self._repo.is_recipient(
                cap.id, viewer_id, self._community_id
            ):
                raise NotFoundError(_("Capsule not found"))
        full = cap.opened_at is not None or cap.author_id == viewer_id
        return (await self._build([cap], full=full))[0]

    async def delete(self, capsule_id: uuid.UUID, actor_id: uuid.UUID) -> None:
        """@brief Soft-delete (author only)."""
        await self._require_feature()
        cap = await self._repo.get(capsule_id, self._community_id)
        if cap is None:
            raise NotFoundError(_("Capsule not found"))
        if cap.author_id != actor_id:
            raise AuthorizationError(_("Only the author can delete a capsule"))
        await self._repo.delete(cap, datetime.now(UTC))

    async def open_due(self, now: datetime) -> int:
        """
        @brief Open every due capsule and notify each recipient once.
        @return Number of capsules opened.
        """
        caps = await self._repo.claim_due(now)
        for cap in caps:
            names = await self._repo.author_names([cap.author_id])
            author_name = names.get(cap.author_id, "")
            for uid in await self._repo.resolve_user_ids(cap):
                await self._notify.notify(
                    uid,
                    "capsule_opened",
                    {
                        "message": _("A time capsule from %(name)s just opened")
                        % {"name": author_name},
                        "link": f"/app/capsules/{cap.id}",
                        "capsule_id": str(cap.id),
                        "title": cap.title,
                        "author_name": author_name,
                    },
                    cap.author_id,
                )
        return len(caps)


def _summary(kinds: list[str]) -> str:
    """@brief Short audience text such as ``2 people, 1 groups`` or ``Everyone``."""
    if "community" in kinds:
        return "Everyone"
    return ", ".join(f"{kinds.count(k)} {_PLURAL[k]}" for k in dict.fromkeys(kinds))
