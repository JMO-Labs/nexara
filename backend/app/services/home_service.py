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

        since = user.last_seen_at if user.last_seen_at else now - timedelta(hours=24)

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
        cursor: str | None = None,
        source: str = "all",
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        @brief Aggregate media across user's visible subgroups.

        Fetches media from each subgroup the user can see, merges, and
        truncates to ``limit``. Does not guarantee strict chronological
        ordering across subgroups — items are returned in per-subgroup order.

        @param user Authenticated User model instance.
        @param limit Maximum number of items to return (capped at 200).
        @param cursor Pagination cursor (currently ignored in multi-subgroup mode).
        @param source Media source filter: 'post', 'gallery', 'event', or 'all'.
        @return Tuple of (items, next_cursor).
        """
        limit = min(limit, 200)

        subgroups = await self._subgroup_repo.list_visible_for_user(
            self._community_id,
            user.id,
        )

        if not subgroups:
            return [], None

        all_items: list[dict[str, Any]] = []
        for sg in subgroups:
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

        truncated = all_items[:limit]
        next_cursor = None  # Multi-subgroup cursor pagination is not implemented
        return truncated, next_cursor
