"""
@file story_service.py
@brief Story requests: ask, answer, silent decline, the Stories tab, and the
       daily reminder (day 14, once) / expiry (day 30) jobs.

A decline is silent: nothing is sent and the asker's view maps ``declined`` to
``open`` until the request expires.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from app.core.exceptions import AppError, NotFoundError
from app.core.features import is_enabled, require_feature
from app.core.i18n import _
from app.models.story_request import StoryRequest
from app.repositories.community_repo import CommunityRepository
from app.repositories.story_repo import LIVE, StoryRepository
from app.schemas.story import StoryItem, StoryList, StoryPerson, StoryRequestList, StoryRequestOut
from app.services.notification_service import NotificationService

MAX_PENDING = 5
"""@brief Open asks allowed from one asker to one teller."""

QUESTIONS_FILE = Path(__file__).resolve().parents[2] / "data" / "story_questions.json"


@lru_cache(maxsize=1)
def question_bank() -> list[str]:
    """@return The built-in story-question suggestions."""
    return list(json.loads(QUESTIONS_FILE.read_text(encoding="utf-8")))


class StoryService:
    """@brief Business rules for story requests."""

    def __init__(
        self,
        repo: StoryRepository,
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
            require_feature(community, "voice_stories")

    async def _out(
        self, rows: list[StoryRequest], viewer_id: uuid.UUID, now: datetime
    ) -> list[StoryRequestOut]:
        names = await self._repo.names(list({i for r in rows for i in (r.asker_id, r.teller_id)}))
        out = []
        for r in rows:
            status = r.status
            if status in LIVE and r.expires_at <= now:
                status = "expired"
            elif status == "declined" and viewer_id == r.asker_id:
                status = "open"  # silent decline
            out.append(
                StoryRequestOut(
                    id=r.id,
                    asker=StoryPerson(id=r.asker_id, display_name=names.get(r.asker_id, "")),
                    teller=StoryPerson(id=r.teller_id, display_name=names.get(r.teller_id, "")),
                    question=r.question,
                    status=status,
                    post_id=r.post_id,
                    created_at=r.created_at,
                    expires_at=r.expires_at,
                )
            )
        return out

    async def _party(self, request_id: uuid.UUID, user_id: uuid.UUID) -> StoryRequest:
        """@brief Load a request the user is a party to, else 404 (no existence leak)."""
        row = await self._repo.get(request_id, self._community_id)
        if row is None or user_id not in (row.asker_id, row.teller_id):
            raise NotFoundError(_("Story request not found"))
        return row

    async def ask(
        self, asker_id: uuid.UUID, teller_id: uuid.UUID, question: str
    ) -> StoryRequestOut:
        """
        @brief Ask a member for a story and notify them.
        @raises AppError 422 for self, blank question or too many pending asks.
        @raises NotFoundError for unknown, blocked or memorialized members.
        """
        await self._require_feature()
        text = question.strip()
        if not text or len(text) > 280:
            raise AppError("VALIDATION_ERROR", _("Question must be 1 to 280 characters"), 422)
        if teller_id == asker_id:
            raise AppError("VALIDATION_ERROR", _("You cannot ask yourself"), 422)
        if not await self._repo.usable_pair(teller_id, asker_id, self._community_id):
            raise NotFoundError(_("Member not found"))
        now = datetime.now(UTC)
        if await self._repo.count_pending(asker_id, teller_id, now) >= MAX_PENDING:
            raise AppError(
                "STORY_LIMIT", _("You have too many open questions for this person"), 422
            )
        row = await self._repo.create(self._community_id, asker_id, teller_id, text, now)
        await self._send_request(row)
        return (await self._out([row], asker_id, now))[0]

    async def _send_request(self, row: StoryRequest) -> None:
        name = (await self._repo.names([row.asker_id])).get(row.asker_id, "")
        await self._notify.notify(
            row.teller_id,
            "story_request",
            {
                "message": _("%(name)s would like to hear a story") % {"name": name},
                "link": f"/app/members/{row.teller_id}?tab=stories",
                "request_id": str(row.id),
                "question": row.question,
                "asker_name": name,
            },
            row.asker_id,
        )

    async def list_for(self, user_id: uuid.UUID) -> StoryRequestList:
        """@return Incoming open asks and the user's own outgoing asks."""
        await self._require_feature()
        now = datetime.now(UTC)
        rows = await self._repo.list_for(user_id, self._community_id, now)
        out = await self._out(rows, user_id, now)
        return StoryRequestList(
            incoming=[o for o in out if o.teller.id == user_id],
            outgoing=[o for o in out if o.asker.id == user_id],
        )

    async def get(self, request_id: uuid.UUID, user_id: uuid.UUID) -> StoryRequestOut:
        """@raises NotFoundError unless the user is the asker or teller."""
        await self._require_feature()
        row = await self._party(request_id, user_id)
        return (await self._out([row], user_id, datetime.now(UTC)))[0]

    async def _open_for_teller(
        self, request_id: uuid.UUID, user_id: uuid.UUID, now: datetime
    ) -> StoryRequest:
        row = await self._party(request_id, user_id)
        if row.teller_id != user_id:
            raise NotFoundError(_("Story request not found"))
        if row.status != "open" or row.expires_at <= now:
            raise AppError("STORY_CLOSED", _("This request is no longer open"), 409)
        return row

    async def decline(self, request_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """@brief Silently decline: no notification, asker still sees ``open``."""
        await self._require_feature()
        row = await self._open_for_teller(request_id, user_id, datetime.now(UTC))
        await self._repo.set_status(row, "declined")

    async def answer(
        self, request_id: uuid.UUID, user_id: uuid.UUID, post_id: uuid.UUID
    ) -> StoryRequestOut:
        """
        @brief Link the teller's own post (audio or text) as the answer and notify the asker.
        @raises AppError 422 when the post is not the teller's or is empty.
        """
        await self._require_feature()
        now = datetime.now(UTC)
        row = await self._open_for_teller(request_id, user_id, now)
        if not await self._repo.answer_post_ok(post_id, user_id, self._community_id):
            raise AppError(
                "VALIDATION_ERROR", _("Pick one of your own posts with audio or text"), 422
            )
        await self._repo.set_status(row, "answered", post_id)
        if not await self._repo.blocked_between(row.asker_id, user_id):
            name = (await self._repo.names([user_id])).get(user_id, "")
            await self._notify.notify(
                row.asker_id,
                "story_answered",
                {
                    "message": _("%(name)s answered your question") % {"name": name},
                    "link": f"/app/post/{post_id}",
                    "request_id": str(row.id),
                    "post_id": str(post_id),
                    "question": row.question,
                    "teller_name": name,
                },
                user_id,
            )
        return (await self._out([row], user_id, now))[0]

    async def stories_of(
        self,
        author_id: uuid.UUID,
        viewer_id: uuid.UUID,
        cursor: datetime | None = None,
        limit: int = 20,
    ) -> StoryList:
        """@return Stories (answers and audio posts) the viewer may open, newest first."""
        await self._require_feature()
        rows, nxt = await self._repo.stories_of(
            author_id, viewer_id, self._community_id, cursor, min(max(limit, 1), 50)
        )
        return StoryList(
            items=[StoryItem(question=q, post=p) for p, q in rows],
            next_cursor=nxt.isoformat() if nxt else None,
        )

    async def pending_for(
        self, teller_id: uuid.UUID, now: datetime
    ) -> list[tuple[StoryRequest, str]]:
        """@return Open asks awaiting the teller (for the recap), with asker names."""
        return [(r, n) for r, n in await self._repo.pending_for(teller_id, self._community_id, now)]

    async def run_daily(self, now: datetime) -> dict[str, int]:
        """
        @brief Send the single day-14 reminder and expire day-30 requests.
        @return ``{"reminded": n, "expired": m}``; no-op when the feature is off.
        """
        community = await self._communities.get(self._community_id)
        if community is None or not is_enabled(community, "voice_stories"):
            return {"reminded": 0, "expired": 0}
        expired = await self._repo.expire_due(self._community_id, now)
        reminded = 0
        for row in await self._repo.claim_reminders(self._community_id, now):
            cid = self._community_id
            if await self._repo.usable_pair(
                row.teller_id, row.asker_id, cid
            ) and await self._repo.usable_pair(row.asker_id, row.teller_id, cid):
                await self._send_request(row)
                reminded += 1
        return {"reminded": reminded, "expired": expired}
