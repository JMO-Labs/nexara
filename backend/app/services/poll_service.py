"""
@file poll_service.py
@brief Business logic for polls, options, and votes.

Orchestrates repository operations with SSE feed_update publishing
via :class:`EventBus` for real-time poll result updates.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.poll import Poll, PollOption
from app.models.post import Post
from app.repositories.poll_repo import PollRepository
from app.schemas.poll import (
    PollCreate,
    PollOptionResponse,
    PollResponse,
    PollResultsResponse,
)
from app.services.realtime.audience import emit_to_audience, resolve_audience
from app.services.realtime.event_bus import EventBus
from app.services.realtime.events import CommunityTarget, poll_voted

logger = structlog.get_logger(__name__)


class PollService:
    """@brief Service layer for poll, option, and vote operations."""

    def __init__(
        self,
        poll_repo: PollRepository,
        community_id: uuid.UUID,
        *,
        event_bus: EventBus | None = None,
    ) -> None:
        self._poll_repo = poll_repo
        self._community_id = community_id
        self._event_bus = event_bus

    def _build_options_with_counts(
        self,
        options: list[PollOption],
        vote_counts: dict[uuid.UUID, int],
    ) -> list[PollOptionResponse]:
        """Build option responses with vote counts."""
        return [
            PollOptionResponse(
                id=opt.id,
                label=opt.label,
                image_media_id=opt.image_media_id,
                position=opt.position,
                vote_count=vote_counts.get(opt.id, 0),
            )
            for opt in options
        ]

    async def create_poll(
        self,
        user_id: uuid.UUID,
        data: PollCreate,
        post_id: uuid.UUID,
    ) -> PollResponse:
        """
        @brief Create a poll with options attached to a post.

        @param user_id Creator UUID.
        @param data Poll creation schema.
        @param post_id Post to attach the poll to.
        @return PollResponse with empty vote counts.
        """
        poll = Poll(
            community_id=self._community_id,
            post_id=post_id,
            created_by=user_id,
            poll_type=data.poll_type,
            question=data.question,
            expires_at=data.expires_at,
            is_anonymous=data.is_anonymous,
            result_visibility=data.result_visibility,
        )
        poll = await self._poll_repo.create(poll)

        options_data = [(opt.label, opt.image_media_id) for opt in data.options]
        await self._poll_repo.create_options(poll.id, options_data)

        options = await self._poll_repo.get_options(poll.id)
        vote_counts = await self._poll_repo.get_vote_counts(poll.id)

        option_responses = self._build_options_with_counts(options, vote_counts)
        total_votes = sum(vote_counts.values())

        return PollResponse(
            id=poll.id,
            post_id=poll.post_id,
            poll_type=poll.poll_type,
            question=poll.question,
            options=option_responses,
            is_anonymous=poll.is_anonymous,
            result_visibility=poll.result_visibility,
            expires_at=poll.expires_at,
            closed=poll.closed,
            total_votes=total_votes,
            user_vote=None,
            created_at=poll.created_at,
        )

    async def cast_vote(
        self,
        poll_id: uuid.UUID,
        user_id: uuid.UUID,
        option_ids: list[uuid.UUID],
    ) -> PollResultsResponse:
        """
        @brief Cast vote(s) on a poll. For single-choice, replaces existing vote.

        @param poll_id Poll UUID.
        @param user_id Voter UUID.
        @param option_ids List of option IDs (one for single, multiple for multiple).
        @return PollResultsResponse with updated counts.
        @raises AppError If poll is closed/expired, invalid option, or wrong count.
        """
        poll = await self._poll_repo.get_by_id(poll_id, community_id=self._community_id)
        if not poll:
            raise NotFoundError(_("Poll not found"))

        if poll.closed:
            raise AppError(
                code="POLL_CLOSED",
                message=_("This poll is closed"),
                status_code=400,
            )

        now = datetime.now(UTC)
        if poll.expires_at and poll.expires_at < now:
            raise AppError(
                code="POLL_EXPIRED",
                message=_("This poll has expired"),
                status_code=400,
            )

        if poll.poll_type == "single" and len(option_ids) != 1:
            raise AppError(
                code="INVALID_VOTE",
                message=_("Single-choice polls require exactly one option"),
                status_code=400,
            )

        options = await self._poll_repo.get_options(poll_id)
        valid_ids = {opt.id for opt in options}
        for oid in option_ids:
            if oid not in valid_ids:
                raise AppError(
                    code="INVALID_OPTION",
                    message=_("Invalid option for this poll"),
                    status_code=400,
                )

        await self._poll_repo.remove_votes(poll_id, user_id)
        for option_id in option_ids:
            await self._poll_repo.cast_vote(poll_id, option_id, user_id)

        vote_counts = await self._poll_repo.get_vote_counts(poll_id)
        option_responses = self._build_options_with_counts(options, vote_counts)
        total_votes = sum(vote_counts.values())

        results = PollResultsResponse(
            poll_id=poll_id,
            options=option_responses,
            total_votes=total_votes,
        )

        if self._event_bus:
            payload = {
                "poll_id": str(poll_id),
                "options": [
                    {"id": str(o.id), "vote_count": o.vote_count} for o in option_responses
                ],
                "total_votes": total_votes,
            }
            event = poll_voted(
                target=CommunityTarget(community_id=self._community_id),
                post_id=poll.post_id,
                poll_id=poll_id,
                results=payload,
            )
            session = self._poll_repo._session
            post = await session.get(Post, poll.post_id) if poll.post_id else None
            audience = await resolve_audience(
                session,
                self._community_id,
                visibility=post.visibility if post else "community",
                subgroup_id=post.subgroup_id if post else None,
                author_id=post.author_id if post else (poll.created_by or user_id),
            )
            await emit_to_audience(self._event_bus, audience, event.type, event.payload)

        return results

    async def get_poll(
        self,
        poll_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> PollResponse:
        """
        @brief Fetch a poll with vote counts and optionally the user's vote.

        Respects result_visibility: after_vote (show only if user voted),
        always (always show), after_expiry (show only if poll expired).

        @param poll_id Poll UUID.
        @param user_id Optional viewer UUID for user_vote and visibility.
        @return PollResponse.
        @raises NotFoundError If poll not found.
        """
        poll = await self._poll_repo.get_by_id(poll_id, community_id=self._community_id)
        if not poll:
            raise NotFoundError(_("Poll not found"))

        options = await self._poll_repo.get_options(poll_id)
        vote_counts = await self._poll_repo.get_vote_counts(poll_id)
        total_votes = sum(vote_counts.values())

        show_results = False
        if poll.result_visibility == "always":
            show_results = True
        elif poll.result_visibility == "after_expiry":
            now = datetime.now(UTC)
            show_results = poll.expires_at is not None and poll.expires_at < now
        elif poll.result_visibility == "after_vote" and user_id:
            show_results = await self._poll_repo.has_user_voted(poll_id, user_id)

        if not show_results:
            vote_counts = {opt.id: 0 for opt in options}

        option_responses = self._build_options_with_counts(options, vote_counts)

        user_vote: list[uuid.UUID] | None = None
        if user_id and show_results:
            user_vote = await self._poll_repo.get_user_votes(poll_id, user_id)

        return PollResponse(
            id=poll.id,
            post_id=poll.post_id,
            poll_type=poll.poll_type,
            question=poll.question,
            options=option_responses,
            is_anonymous=poll.is_anonymous,
            result_visibility=poll.result_visibility,
            expires_at=poll.expires_at,
            closed=poll.closed,
            total_votes=total_votes if show_results else 0,
            user_vote=user_vote,
            created_at=poll.created_at,
        )

    async def get_results(self, poll_id: uuid.UUID) -> PollResultsResponse:
        """
        @brief Fetch poll results (vote counts per option).

        @param poll_id Poll UUID.
        @return PollResultsResponse.
        @raises NotFoundError If poll not found.
        """
        poll = await self._poll_repo.get_by_id(poll_id, community_id=self._community_id)
        if not poll:
            raise NotFoundError(_("Poll not found"))

        options = await self._poll_repo.get_options(poll_id)
        vote_counts = await self._poll_repo.get_vote_counts(poll_id)
        total_votes = sum(vote_counts.values())

        option_responses = self._build_options_with_counts(options, vote_counts)
        return PollResultsResponse(
            poll_id=poll_id,
            options=option_responses,
            total_votes=total_votes,
        )

    async def close_poll(self, poll_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        @brief Close a poll. Only the creator can close.

        @param poll_id Poll UUID.
        @param user_id User requesting close (must be creator).
        @raises NotFoundError If poll not found.
        @raises AuthorizationError If user is not the creator.
        """
        poll = await self._poll_repo.get_by_id(poll_id, community_id=self._community_id)
        if not poll:
            raise NotFoundError(_("Poll not found"))

        if poll.created_by != user_id:
            raise AuthorizationError(_("Only the poll creator can close this poll"))

        await self._poll_repo.update(poll, {"closed": True})
