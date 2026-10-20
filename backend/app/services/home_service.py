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
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        @brief Aggregate media across community-root and/or user's visible subgroups.

        Uses a single union query for efficiency:
        - scope='all': community-root (subgroup_id IS NULL) + viewer's subgroups
        - scope='community': community-root only (subgroup_id IS NULL)
        - scope='subgroup': specific subgroup_id only

        Respects visibility predicates (community / subgroup / private).

        @param user Authenticated User model instance.
        @param limit Maximum number of items to return (capped at 200).
        @param source Media source filter: 'post', 'gallery', 'event', or 'all'.
        @param scope Visibility scope: 'all', 'community', 'subgroup'.
        @param subgroup_id Required when scope='subgroup'; the target subgroup.
        @param cursor Opaque pagination cursor.
        @return Tuple of (items, next_cursor).
        """
        limit = min(limit, 200)

        # Resolve viewer's subgroup IDs for scope='all'
        subgroups = await self._subgroup_repo.list_visible_for_user(
            self._community_id,
            user.id,
        )
        subgroup_ids = [sg.id for sg in subgroups]

        # Call aggregated query with scope
        return await self._media_repo.list_aggregated(
            community_id=self._community_id,
            viewer_id=user.id,
            scope=scope,
            subgroup_id=subgroup_id,
            subgroup_ids=subgroup_ids,
            source=source,
            cursor=cursor,
            limit=limit,
        )
