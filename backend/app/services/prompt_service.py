"""
@file prompt_service.py
@brief Tradition prompt scheduling, firing, and summary generation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import structlog
from dateutil.rrule import rrulestr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.post import Post
from app.models.prompt import Prompt, PromptPost
from app.repositories.post_repo import PostRepository
from app.repositories.prompt_repo import PromptRepository
from app.schemas.prompt import (
    PromptCreate,
    PromptPostDetail,
    PromptPostResponse,
    PromptResponse,
    PromptSummary,
    PromptUpdate,
)

logger = structlog.get_logger(__name__)

MAX_PINNED_PROMPTS = 2
"""@brief Maximum number of simultaneously-pinned prompt posts per community."""


def should_fire(prompt: Prompt, today: date) -> bool:
    """
    @brief Decide whether a prompt should fire on ``today``.

    @param prompt The prompt to evaluate.
    @param today The date to evaluate against (UTC).
    @return True if the prompt's schedule matches today.
    """
    if not prompt.is_enabled:
        return False

    ftype = prompt.frequency_type
    if ftype == "annual_date":
        return prompt.trigger_month == today.month and prompt.trigger_day == today.day
    if ftype == "weekly":
        if prompt.trigger_weekday is None:
            return False
        return today.weekday() == prompt.trigger_weekday
    if ftype == "monthly":
        return prompt.trigger_month_day == today.day
    if ftype == "one_time":
        return prompt.trigger_one_time_date == today
    if ftype == "custom":
        if not prompt.trigger_custom_rule:
            return False
        try:
            dtstart = datetime.combine(today, datetime.min.time())
            rule = rrulestr(prompt.trigger_custom_rule, dtstart=dtstart)
        except Exception:  # noqa: BLE001
            return False
        next_run = rule.after(
            datetime.combine(today - timedelta(days=1), datetime.max.time()),
            inc=True,
        )
        if next_run is None:
            return False
        return next_run.date() == today
    return False


class PromptService:
    """@brief Service layer for tradition prompts."""

    def __init__(
        self,
        prompt_repo: PromptRepository,
        post_repo: PostRepository,
        community_id: uuid.UUID,
        session: AsyncSession,
        *,
        notification_service: Any | None = None,
    ) -> None:
        self._repo = prompt_repo
        self._post_repo = post_repo
        self._community_id = community_id
        self._session = session
        self._notifications = notification_service

    # ── CRUD ──────────────────────────────────────────────────────────

    async def create_prompt(self, user_id: uuid.UUID, data: PromptCreate) -> PromptResponse:
        if data.scope == "subgroup" and data.subgroup_id is None:
            raise AppError(
                code="SUBGROUP_REQUIRED",
                message=_("Subgroup is required for subgroup-scoped prompts"),
                status_code=400,
            )

        prompt = Prompt(
            community_id=self._community_id,
            title=data.title,
            body=data.body,
            source="custom",
            frequency_type=data.frequency_type,
            trigger_month=data.trigger_month,
            trigger_day=data.trigger_day,
            trigger_weekday=data.trigger_weekday,
            trigger_week_interval=data.trigger_week_interval,
            trigger_month_day=data.trigger_month_day,
            trigger_custom_rule=data.trigger_custom_rule,
            trigger_one_time_date=data.trigger_one_time_date,
            active_days=data.active_days,
            scope=data.scope,
            subgroup_id=data.subgroup_id,
            notify_members=data.notify_members,
            notification_body=data.notification_body,
            linked_event_id=data.linked_event_id,
            generate_summary=data.generate_summary,
            prompt_type=data.prompt_type,
            interest_category_slug=data.interest_category_slug,
            interest_capture_hint=data.interest_capture_hint,
            created_by=user_id,
        )
        prompt = await self._repo.create(prompt)
        return PromptResponse.model_validate(prompt)

    async def list_prompts(self) -> list[PromptResponse]:
        rows = await self._repo.list_for_admin(self._community_id)
        return [PromptResponse.model_validate(r) for r in rows]

    async def get_prompt(self, prompt_id: uuid.UUID) -> PromptResponse:
        prompt = await self._repo.get_by_id(prompt_id, community_id=self._community_id)
        if prompt is None:
            raise NotFoundError(_("Prompt not found"))
        return PromptResponse.model_validate(prompt)

    async def update_prompt(self, prompt_id: uuid.UUID, data: PromptUpdate) -> PromptResponse:
        prompt = await self._repo.get_by_id(prompt_id, community_id=self._community_id)
        if prompt is None:
            raise NotFoundError(_("Prompt not found"))
        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(UTC)
        prompt = await self._repo.update(prompt, update_data)
        return PromptResponse.model_validate(prompt)

    async def delete_prompt(self, prompt_id: uuid.UUID, user_id: uuid.UUID) -> None:
        prompt = await self._repo.get_by_id(prompt_id, community_id=self._community_id)
        if prompt is None:
            raise NotFoundError(_("Prompt not found"))
        if prompt.source == "builtin":
            raise AuthorizationError(_("Built-in prompts cannot be deleted; disable them instead"))
        await self._session.delete(prompt)
        await self._session.flush()

    # ── Firing ────────────────────────────────────────────────────────

    async def fire_due_prompts(self, today: date | None = None) -> int:
        """
        @brief Fire all enabled prompts whose schedule matches today.

        Enforces MAX_PINNED_PROMPTS — if already at limit, skips additional
        prompts (logs a warning). Idempotent per ``(prompt_id, today)``.

        @param today Date to evaluate (defaults to UTC today).
        @return Number of prompts fired.
        """
        today = today or datetime.now(UTC).date()
        now = datetime.now(UTC)
        fired = 0

        prompts = await self._repo.list_enabled(self._community_id)
        active = await self._repo.count_active_pinned(self._community_id, now)

        for prompt in prompts:
            if not should_fire(prompt, today):
                continue
            existing = await self._repo.get_post_for_today(prompt.id, today)
            if existing is not None:
                continue
            if active >= MAX_PINNED_PROMPTS:
                logger.warning(
                    "prompt_skipped_max_pinned",
                    prompt_id=str(prompt.id),
                    active=active,
                )
                continue

            post = Post(
                community_id=self._community_id,
                author_id=prompt.created_by,
                content=f"**{prompt.title}**\n\n{prompt.body}",
                is_pinned=True,
            )
            post = await self._post_repo.create(post)

            expires_at = now + timedelta(days=prompt.active_days)
            tracker = PromptPost(
                community_id=self._community_id,
                prompt_id=prompt.id,
                post_id=post.id,
                fired_at=today,
                expires_at=expires_at,
            )
            await self._repo.create_prompt_post(tracker)
            active += 1
            fired += 1

            if prompt.notify_members and self._notifications:
                try:
                    await self._notifications.notify(
                        user_id=prompt.created_by,
                        type="prompt",
                        payload={
                            "prompt_id": str(prompt.id),
                            "post_id": str(post.id),
                            "message": prompt.notification_body or prompt.title,
                            "link": f"/app/posts/{post.id}",
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("prompt_notify_failed", error=str(exc))

        return fired

    # ── Summary ───────────────────────────────────────────────────────

    async def _collect_summary_media_ids(self, prompt_id: uuid.UUID) -> list[uuid.UUID]:
        """
        @brief Collect media IDs from replies to a prompt, up to 9 total.

        @param prompt_id Prompt UUID.
        @return List of media IDs (max 9) from prompt replies.
        """
        replies = await self._post_repo.list_replies_for_prompt(prompt_id, limit=50)
        media_ids: list[uuid.UUID] = []
        for reply in replies:
            if "media_ids" in reply:
                media_ids.extend(reply["media_ids"])
            if len(media_ids) >= 9:
                break
        return media_ids[:9]

    async def finalise_expired(self, now: datetime | None = None) -> int:
        """
        @brief Generate summary posts for prompts whose active window expired.

        For each expired prompt post:
          - Create a regular (non-pinned) summary post in the feed
          - Unpin the original prompt post
          - Mark the tracker as finalised
          - Notify the prompt author of the summary

        @param now Reference time (defaults to UTC now).
        @return Number of prompts finalised.
        """
        now = now or datetime.now(UTC)
        finalised = 0

        expired = await self._repo.list_expired_unfinalised(self._community_id, now)

        for tracker in expired:
            prompt = await self._repo.get_by_id(tracker.prompt_id, community_id=self._community_id)

            summary_post_id: uuid.UUID | None = None
            if prompt and prompt.generate_summary:
                summary_content = self._build_summary_content(prompt, tracker)
                media_ids = await self._collect_summary_media_ids(tracker.prompt_id)  # noqa: F841
                summary = Post(
                    community_id=self._community_id,
                    author_id=prompt.created_by,
                    content=summary_content,
                    is_pinned=False,
                )
                summary = await self._post_repo.create(summary)
                summary_post_id = summary.id
                # TODO: Attach collected media_ids to summary post if needed
                # Currently collected media_ids are available but not attached

                if self._notifications:
                    try:
                        await self._notifications.notify(
                            user_id=prompt.created_by,
                            type="prompt_summary",
                            payload={
                                "prompt_id": str(prompt.id),
                                "summary_post_id": str(summary.id),
                                "message": _("Prompt summary is ready"),
                                "link": f"/app/posts/{summary.id}",
                            },
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("summary_notify_failed", error=str(exc))

            # Unpin the original prompt post.
            original = await self._post_repo.get_by_id(
                tracker.post_id, community_id=self._community_id
            )
            if original is not None:
                original.is_pinned = False
                await self._session.flush()

            await self._repo.finalise(tracker, summary_post_id)
            finalised += 1

        return finalised

    @staticmethod
    def _build_summary_content(prompt: Prompt, tracker: PromptPost) -> str:
        """@brief Render a basic summary post body."""
        return (
            f"**Summary: {prompt.title}**\n\n"
            f"_{tracker.response_count} responses received._\n\n"
            f"Thank you to everyone who shared!"
        )

    async def list_active(self) -> list[PromptPostDetail]:
        """@brief List currently-pinned prompt posts with prompt details."""
        rows = await self._repo.list_active(self._community_id, datetime.now(UTC))
        prompts = await self._repo.get_by_ids(
            list({r.prompt_id for r in rows}), community_id=self._community_id
        )
        by_id = {p.id: p for p in prompts}
        return [self._detail(r, by_id[r.prompt_id]) for r in rows if r.prompt_id in by_id]

    async def get_prompt_post(self, prompt_post_id: uuid.UUID) -> PromptPostDetail:
        """@brief Get one prompt post with prompt details; 404 if absent."""
        pp = await self._repo.get_prompt_post(prompt_post_id, community_id=self._community_id)
        prompt = (
            await self._repo.get_by_id(pp.prompt_id, community_id=self._community_id)
            if pp is not None
            else None
        )
        if pp is None or prompt is None:
            raise NotFoundError(_("Prompt post not found"))
        return self._detail(pp, prompt)

    @staticmethod
    def _detail(pp: PromptPost, prompt: Prompt) -> PromptPostDetail:
        base = PromptPostResponse.model_validate(pp).model_dump()
        return PromptPostDetail(**base, prompt=PromptSummary.model_validate(prompt))
