"""
@file activity_repo.py
@brief ActivityRepository for writing and reading community activity events.

Provides record() (append-only), invalidate() (soft-delete), and list_for_user()
(viewer-scoped reads with visibility + block filtering).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, cast

import structlog
from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.engine import CursorResult

from app.models.activity_event import ActivityEvent
from app.repositories.base import BaseRepository

logger = structlog.get_logger(__name__)


class ActivityRepository(BaseRepository[ActivityEvent]):
    """
    @brief Append-only activity event repository.

    Methods:
    - record(): insert a new event; wraps in try/except so failure never rolls back caller.
    - invalidate(): mark events is_active=false for deleted objects.
    - list_for_user(): fetch viewer-scoped feed with visibility + block filtering.
    """

    model = ActivityEvent

    async def record(
        self,
        *,
        community_id: uuid.UUID,
        actor_id: uuid.UUID,
        verb: str,
        object_type: str,
        object_id: uuid.UUID,
        subgroup_id: uuid.UUID | None,
        visibility: str,
        target_type: str | None = None,
        target_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        @brief Record a new activity event (best-effort, never fails caller).

        Wraps insert in try/except + logger.exception so activity-row write
        failure never rolls back the underlying domain commit. The domain
        operation is the source of truth; the activity log is best-effort.

        @param community_id Community UUID.
        @param actor_id UUID of user who triggered the event.
        @param verb Action name, e.g. 'post.created', 'media.uploaded'.
        @param object_type Type of object affected, e.g. 'post', 'media'.
        @param object_id UUID of the affected object.
        @param subgroup_id Optional subgroup scope (null = community-root).
        @param visibility Visibility level ('community', 'subgroup', 'private').
        @param target_type Optional container type ('subgroup', 'community', 'post', etc.).
        @param target_id Optional container UUID.
        @param metadata Optional JSONB snapshot (actor_name, object_title, etc.).
        @return None.
        """
        try:
            event = ActivityEvent(
                community_id=community_id,
                actor_id=actor_id,
                verb=verb,
                object_type=object_type,
                object_id=object_id,
                subgroup_id=subgroup_id,
                visibility=visibility,
                target_type=target_type,
                target_id=target_id,
                event_metadata=metadata or {},
            )
            self._session.add(event)
            await self._session.flush()
        except Exception as e:
            logger.exception(
                "activity_record_failed",
                verb=verb,
                object_type=object_type,
                object_id=str(object_id),
                error=str(e),
            )

    async def invalidate(self, object_type: str, object_id: uuid.UUID) -> None:
        """
        @brief Mark activity events for a deleted object as is_active=false.

        Called after hard-delete of a domain object; flips is_active so
        the event is filtered out of feeds.

        @param object_type Type of deleted object, e.g. 'post'.
        @param object_id UUID of deleted object.
        @return None.
        """
        stmt = (
            update(ActivityEvent)
            .where(
                and_(
                    ActivityEvent.object_type == object_type,
                    ActivityEvent.object_id == object_id,
                )
            )
            .values(is_active=False)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def list_for_user(
        self,
        *,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        viewer_subgroup_ids: list[uuid.UUID],
        cursor: datetime | None = None,
        limit: int = 30,
    ) -> list[ActivityEvent]:
        """
        @brief Fetch viewer-scoped activity feed with visibility + block filtering.

        Filters by:
        1. Community scope
        2. is_active=true
        3. Excludes viewer's own actions (actor_id != viewer_id)
        4. Visibility predicate: community (always) OR subgroup (if viewer in it)
        5. Block filter: excludes actors viewer/who blocked viewer

        Cursor-based pagination on created_at DESC.

        @param community_id Community UUID.
        @param viewer_id UUID of viewing user.
        @param viewer_subgroup_ids List of subgroup UUIDs viewer belongs to.
        @param cursor Optional datetime cursor (fetch events before this time).
        @param limit Max items (default 30).
        @return List of ActivityEvent ordered by created_at DESC.
        """
        stmt = select(ActivityEvent).where(
            and_(
                ActivityEvent.community_id == community_id,
                ActivityEvent.is_active,
                ActivityEvent.actor_id != viewer_id,
                or_(
                    ActivityEvent.visibility == "community",
                    and_(
                        ActivityEvent.visibility == "subgroup",
                        ActivityEvent.subgroup_id.in_(viewer_subgroup_ids),
                    ),
                ),
            )
        )

        if cursor is not None:
            stmt = stmt.where(ActivityEvent.created_at < cursor)

        stmt = stmt.order_by(ActivityEvent.created_at.desc()).limit(limit)

        # Apply block filter (excludes actors blocked by viewer or who blocked viewer)
        stmt = self.apply_block_filter(stmt, viewer_id)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_older_than_days(self, days: int = 30) -> int:
        """
        @brief Delete activity events older than N days.

        Called by the prune_activity_events Celery task.

        @param days Number of days to retain (default 30).
        @return Number of deleted rows.
        """
        from datetime import datetime as _dt
        from datetime import timedelta

        cutoff = _dt.now(UTC) - timedelta(days=days)
        stmt = delete(ActivityEvent).where(ActivityEvent.created_at < cutoff)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return cast(CursorResult[Any], result).rowcount or 0
