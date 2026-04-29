"""
@file home_service.py
@brief Service orchestrating home-page summary and media aggregation.

Reuses existing repositories via dependency injection. Does not raise
raw HTTP exceptions — only uses core/exceptions.py error types.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.models.user import User
from app.repositories.event_repo import EventRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.post_repo import PostRepository
from app.repositories.subgroup_media_repo import SubgroupMediaRepository
from app.repositories.subgroup_repo import SubgroupRepository
from app.schemas.home import HomeSummaryResponse


class HomeService:
    """
    @brief Orchestrates home-page summary and media aggregation.

    @param post_repo PostRepository instance.
    @param event_repo EventRepository instance.
    @param notification_repo NotificationRepository instance.
    @param subgroup_repo SubgroupRepository instance.
    @param media_repo SubgroupMediaRepository instance.
    @param community_id Community UUID scope.
    """

    def __init__(
        self,
        post_repo: PostRepository,
        event_repo: EventRepository,
        notification_repo: NotificationRepository,
        subgroup_repo: SubgroupRepository,
        media_repo: SubgroupMediaRepository,
        community_id: uuid.UUID,
    ) -> None:
        self._post_repo = post_repo
        self._event_repo = event_repo
        self._notification_repo = notification_repo
        self._subgroup_repo = subgroup_repo
        self._media_repo = media_repo
        self._community_id = community_id

    async def summary(
        self,
        user: User,
        now: datetime | None = None,
    ) -> HomeSummaryResponse:
        """
        @brief Build home summary stats for the authenticated user.

        @param user Authenticated User model instance.
        @param now Override for current time (useful in tests).
        @return HomeSummaryResponse with counts.
        """
        if now is None:
            now = datetime.now(UTC)

        since = user.last_seen_at or (now - timedelta(hours=24))

        # Resolve subgroup IDs once; used for both post and event visibility scoping.
        subgroups = await self._subgroup_repo.list_visible_for_user(
            self._community_id,
            user.id,
        )
        subgroup_ids = [sg.id for sg in subgroups]

        new_posts = await self._post_repo.count_new_since(
            community_id=self._community_id,
            viewer_id=user.id,
            since=since,
            subgroup_ids=subgroup_ids,
        )

        events = await self._event_repo.list_in_range(
            self._community_id,
            start=now,
            end=now + timedelta(days=7),
            viewer_id=user.id,
            subgroup_ids=subgroup_ids,
        )

        unread = await self._notification_repo.get_unread_count(user.id)

        return HomeSummaryResponse(
            new_posts=new_posts,
            upcoming_events=len(events),
            unread_notifications=unread,
        )

    async def list_media(
        self,
        user: User,
        limit: int = 24,
        source: str = "all",
        scope: str = "all",
        subgroup_id: uuid.UUID | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        @brief Aggregate media across user's visible subgroups.

        Fetches media from each subgroup the user can see, merges, and
        truncates to ``limit``. Does not guarantee strict chronological
        ordering across subgroups — items are returned in per-subgroup order.

        Pagination not yet implemented — Phase 2 will add cursor support
        across multiple subgroups.

        @param user Authenticated User model instance.
        @param limit Maximum number of items to return (capped at 200).
        @param source Media source filter: 'post', 'gallery', 'event', or 'all'.
        @param scope Visibility scope: 'all', 'community', 'subgroup', 'personal'.
        @param subgroup_id Required when scope='subgroup'; the target subgroup.
        @return Tuple of (items, next_cursor).
        """
        limit = min(limit, 200)

        subgroups = await self._subgroup_repo.list_visible_for_user(
            self._community_id,
            user.id,
        )

        # Pick the subgroups to query based on scope.
        if scope == "subgroup":
            if subgroup_id is None:
                return [], None
            target = [sg for sg in subgroups if sg.id == subgroup_id]
        elif scope == "community":
            # No subgroup-specific media in 'community' scope; rely on the
            # subgroup_media_repo's default behaviour to return only items
            # without a subgroup link is not yet implemented. For now treat
            # community-scope as 'all' minus per-subgroup duplicates.
            target = subgroups
        elif scope == "personal":
            # Personal: only items the user is the author/owner of. Filtered
            # post-hoc since the repo doesn't expose owner_id directly.
            target = subgroups
        else:
            target = subgroups

        if not target:
            return [], None

        # TODO(phase-2): bulk multi-subgroup query instead of N per-subgroup calls.
        # Cap at 25 subgroups to bound N+1 query cost.
        _max_subgroups = 25
        capped = target[:_max_subgroups]

        all_items: list[dict[str, Any]] = []
        for sg in capped:
            items, _ = await self._media_repo.list_media(
                subgroup_id=sg.id,
                viewer_id=user.id,
                source=source,
                cursor=None,
                limit=limit,
            )
            all_items.extend(items)
            if len(all_items) >= limit:
                break

        if scope == "personal":
            user_id_str = str(user.id)
            all_items = [
                it
                for it in all_items
                if str(it.get("uploader_id") or it.get("author_id") or "")
                == user_id_str
            ]

        truncated = all_items[:limit]
        next_cursor = None  # Pagination not yet implemented (see docstring)
        return truncated, next_cursor
