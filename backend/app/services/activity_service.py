"""
@file activity_service.py
@brief ActivityService for unified activity feed aggregation.

Handles read-time existence check, aggregation (60-min window), and feed assembly
for the home activity widget.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import structlog

from app.models.user import User
from app.repositories.activity_repo import ActivityRepository
from app.repositories.event_repo import EventRepository
from app.repositories.gallery_repo import GalleryRepository
from app.repositories.post_repo import PostRepository
from app.repositories.subgroup_media_repo import SubgroupMediaRepository
from app.repositories.subgroup_repo import SubgroupRepository
from app.schemas.activity import ActivityFeedResponse, ActivityItem

logger = structlog.get_logger(__name__)

# Aggregation window: consecutive events within this many minutes are collapsed
AGGREGATION_WINDOW_MINUTES = 60


class ActivityService:
    """
    @brief Service for reading and aggregating activity feed events.

    Orchestrates:
    1. Fetching visibility-filtered activity events from the repo.
    2. Resolving viewer's subgroup membership for filtering.
    3. Read-time existence check (drop events whose objects are deleted).
    4. Read-time aggregation (collapse consecutive same actor/verb/target within 60 min).
    5. Building ActivityItem responses with metadata from snapshots.

    @param activity_repo ActivityRepository instance.
    @param subgroup_repo SubgroupRepository instance.
    @param post_repo PostRepository instance (for exists_many).
    @param event_repo EventRepository instance (for exists_many).
    @param gallery_repo GalleryRepository instance (for exists_many).
    @param media_repo SubgroupMediaRepository instance (for exists_many).
    @param community_id Community UUID scope.
    """

    def __init__(
        self,
        activity_repo: ActivityRepository,
        subgroup_repo: SubgroupRepository,
        post_repo: PostRepository,
        event_repo: EventRepository,
        gallery_repo: GalleryRepository,
        media_repo: SubgroupMediaRepository,
        community_id: uuid.UUID,
    ) -> None:
        self._activity_repo = activity_repo
        self._subgroup_repo = subgroup_repo
        self._post_repo = post_repo
        self._event_repo = event_repo
        self._gallery_repo = gallery_repo
        self._media_repo = media_repo
        self._community_id = community_id

    async def list_for_user(
        self,
        user: User,
        cursor: datetime | None = None,
        limit: int = 30,
    ) -> ActivityFeedResponse:
        """
        @brief Fetch aggregated activity feed for authenticated user.

        Flow:
        1. Resolve viewer's subgroup membership.
        2. Query visibility-filtered events from activity_repo.
        3. Batch existence check per object_type; drop missing objects.
        4. Collapse consecutive same (actor_id, verb, target_type, target_id)
           with created_at deltas ≤60 min into single item with count.
        5. Build ActivityItem per group with metadata from snapshot.
        6. Compute next_cursor = oldest created_at if len(items) == limit.

        @param user Authenticated User instance.
        @param cursor Optional datetime cursor (fetch events before this time).
        @param limit Max items (default 30, capped at 100).
        @return ActivityFeedResponse with paginated items.
        """
        limit = min(limit, 100)

        # 1. Resolve viewer's subgroup membership
        subgroups = await self._subgroup_repo.list_visible_for_user(
            self._community_id,
            user.id,
        )
        viewer_subgroup_ids = [sg.id for sg in subgroups]

        # 2. Fetch visibility-filtered events (excludes viewer's own actions)
        events = await self._activity_repo.list_for_user(
            community_id=self._community_id,
            viewer_id=user.id,
            viewer_subgroup_ids=viewer_subgroup_ids,
            cursor=cursor,
            limit=limit,
        )

        # 3. Read-time existence check: group by object_type, batch check each
        events = await self._filter_dead_objects(events)

        # 4. Aggregation: collapse consecutive same (actor, verb, target) within 60 min
        aggregated = self._aggregate_events(events)

        # 5. Build ActivityItem responses
        items = [
            ActivityItem(
                id=group[0].id,  # Newest event in group
                actor_id=group[0].actor_id,
                actor_name=group[0].event_metadata.get("actor_name", ""),
                verb=group[0].verb,
                object_type=group[0].object_type,
                object_id=group[0].object_id,
                container_type=group[0].target_type,
                container_title=group[0].event_metadata.get("container_title"),
                object_title=group[0].event_metadata.get("object_title"),
                count=len(group),
                created_at=group[0].created_at,
            )
            for group in aggregated
        ]

        # 6. Compute next_cursor
        next_cursor = None
        if len(events) == limit and items:
            next_cursor = items[-1].created_at

        return ActivityFeedResponse(
            items=items,
            next_cursor=next_cursor,
        )

    async def _filter_dead_objects(self, events: list[Any]) -> list[Any]:
        """
        @brief Drop events whose objects no longer exist (read-time existence check).

        Groups events by object_type, batch-checks existence for each type,
        and filters out missing objects.

        @param events List of ActivityEvent instances from repo.
        @return Filtered list with dead objects removed.
        """
        if not events:
            return events

        # Group events by object_type
        type_to_events: dict[str, list[Any]] = {}
        for event in events:
            event_type = event.object_type
            if event_type not in type_to_events:
                type_to_events[event_type] = []
            type_to_events[event_type].append(event)

        # Batch existence check per type
        type_to_existing_ids = {}
        if "post" in type_to_events:
            ids = {e.object_id for e in type_to_events["post"]}
            type_to_existing_ids["post"] = await self._post_repo.exists_many(ids)
        if "event" in type_to_events:
            ids = {e.object_id for e in type_to_events["event"]}
            type_to_existing_ids["event"] = await self._event_repo.exists_many(ids)
        if "gallery" in type_to_events:
            ids = {e.object_id for e in type_to_events["gallery"]}
            type_to_existing_ids["gallery"] = await self._gallery_repo.exists_many(ids)
        if "media" in type_to_events:
            ids = {e.object_id for e in type_to_events["media"]}
            type_to_existing_ids["media"] = await self._media_repo.exists_many(ids)
        # Comment, reaction, rsvp, chat, member, subgroup, prompt events
        # are accepted as-is (their existence is implicitly by the activity row).

        # Filter: keep only events whose object exists
        filtered = []
        for event in events:
            event_type = event.object_type
            if event_type in type_to_existing_ids:
                if event.object_id in type_to_existing_ids[event_type]:
                    filtered.append(event)
            else:
                # Types without explicit existence check (comments, reactions, etc.)
                filtered.append(event)

        return filtered

    def _aggregate_events(self, events: list[Any]) -> list[list[Any]]:
        """
        @brief Collapse consecutive same (actor_id, verb, target_type, target_id)
               with created_at deltas ≤60 min into single group.

        Walk DESC-ordered list (already sorted by repo), accumulate runs of same
        key, yield groups. Newest event stays first in each group.

        @param events List of ActivityEvent, ordered DESC by created_at.
        @return List of groups, each group is list of consecutive events.
        """
        if not events:
            return []

        # Defensive: ensure DESC ordering (newest first) so group[0] is always newest.
        events = sorted(events, key=lambda e: e.created_at, reverse=True)

        groups = []
        current_group = [events[0]]
        current_key = (
            events[0].actor_id,
            events[0].verb,
            events[0].target_type,
            events[0].target_id,
        )

        for event in events[1:]:
            key = (
                event.actor_id,
                event.verb,
                event.target_type,
                event.target_id,
            )

            # Check if same key and within 60-min window
            time_delta = current_group[0].created_at - event.created_at
            if key == current_key and time_delta < timedelta(minutes=AGGREGATION_WINDOW_MINUTES):
                current_group.append(event)
            else:
                # Start new group
                groups.append(current_group)
                current_group = [event]
                current_key = key

        # Don't forget the last group
        if current_group:
            groups.append(current_group)

        return groups
