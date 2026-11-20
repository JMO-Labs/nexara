"""
@file home_feed_service.py
@brief HomeFeedService: merges viewer-scoped posts and activity into one feed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models.user import User
from app.repositories.post_repo import PostRepository
from app.repositories.subgroup_repo import SubgroupMemberRepository
from app.schemas.home_feed import ActivityFeedItem, FeedItem, HomeFeedResponse, PostFeedItem
from app.services.activity_service import ActivityService

ACTIVITY_WINDOW_SECONDS = 10


class HomeFeedService:
    """
    @brief Merge posts and activity by created_at desc.

    Visibility and block filtering are delegated to the repos; the viewer's
    direct subgroup memberships scope both streams.

    @param post_repo PostRepository.
    @param activity_service ActivityService (aggregation, existence checks).
    @param member_repo SubgroupMemberRepository (viewer memberships).
    @param community_id Community scope.
    """

    def __init__(
        self,
        post_repo: PostRepository,
        activity_service: ActivityService,
        member_repo: SubgroupMemberRepository,
        community_id: uuid.UUID,
    ) -> None:
        self._posts = post_repo
        self._activity = activity_service
        self._members = member_repo
        self._community_id = community_id

    async def list(self, viewer: User, cursor: str | None, limit: int) -> HomeFeedResponse:
        """
        @brief Return one page of the merged feed.
        @param viewer Authenticated user.
        @param cursor ISO timestamp of the last item seen, or None.
        @param limit Page size.
        @return HomeFeedResponse; next_cursor is the last item's created_at when more may exist.
        """
        subgroup_ids = list((await self._members.list_my_roles(viewer.id)).keys())
        cursor_ts = _parse(cursor)
        posts, post_next = await self._posts.list_feed(
            self._community_id,
            viewer_id=viewer.id,
            cursor=cursor_ts.isoformat() if cursor_ts else None,
            limit=limit,
            subgroup_ids=subgroup_ids,
        )
        act = await self._activity.list_for_user(
            viewer,
            cursor=cursor_ts,
            limit=limit,
            window_seconds=ACTIVITY_WINDOW_SECONDS,
            subgroup_ids=subgroup_ids,
        )
        merged: list[FeedItem] = [
            PostFeedItem(id=p["id"], created_at=_aware(p["created_at"]), post=p) for p in posts
        ]
        merged += [
            ActivityFeedItem(id=a.id, created_at=_aware(a.created_at), activity=a)
            for a in act.items
            if a.verb != "post.created" and not a.verb.startswith("chat.")
        ]
        merged.sort(key=lambda i: i.created_at, reverse=True)
        deduped = list({(i.kind, i.id): i for i in reversed(merged)}.values())[::-1]
        page = deduped[:limit]
        more = len(deduped) > limit or post_next is not None or act.next_cursor is not None
        # ponytail: timestamp cursor; ties at the page boundary may skip.
        next_cursor = page[-1].created_at.isoformat() if page and more else None
        return HomeFeedResponse(items=page, next_cursor=next_cursor)


def _aware(value: datetime | str) -> datetime:
    """
    @brief Coerce a timestamp to an aware UTC datetime.

    Post rows arrive serialized (ISO strings) and some activity rows are naive;
    mixing them broke sorting and produced naive cursors (500 on page 2).
    """
    dt = datetime.fromisoformat(value) if isinstance(value, str) else value
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _parse(cursor: str | None) -> datetime | None:
    """@brief Parse an ISO cursor as an aware UTC datetime; invalid values are ignored."""
    try:
        return _aware(datetime.fromisoformat(cursor)) if cursor else None
    except ValueError:
        return None
