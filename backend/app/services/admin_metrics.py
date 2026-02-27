"""
@file admin_metrics.py
@brief Prometheus metric extraction and community metrics aggregation.

Helpers to read in-memory Prometheus gauges/counters and build
CommunityMetrics from DB. Used by AdminService.get_metrics().
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.metrics import (
    celery_queue_depth,
    users_online,
    waf_blocks_total,
)
from app.models.media import Media
from app.models.post import Post
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.admin import (
    CommunityMetrics,
    MetricsResponse,
    SystemMetrics,
    WafMetrics,
)

_PROCESS_START_TIME: float = time.time()
"""@brief Process start time for uptime calculation."""


def _gauge_value(gauge) -> int:
    """@brief Get value from an unlabeled Gauge."""
    try:
        val = gauge._value.get()
        return int(val) if val is not None else 0
    except Exception:
        return 0


def _gauge_total(gauge) -> int:
    """@brief Sum all label values from a labeled Gauge, or return single value."""
    try:
        if hasattr(gauge, "_metrics") and gauge._metrics:
            return int(sum(m._value.get() for m in gauge._metrics.values()))
        return _gauge_value(gauge)
    except Exception:
        return 0


def _counter_by_label(counter) -> dict[str, int]:
    """@brief Extract per-label values from a labeled Counter."""
    result: dict[str, int] = {}
    if not hasattr(counter, "_metrics"):
        return result
    for labels, child in counter._metrics.items():
        if isinstance(labels, tuple) and len(labels) == 1:
            result[str(labels[0])] = int(child._value.get())
        elif isinstance(labels, tuple):
            key = "_".join(str(l) for l in labels)
            result[key] = int(child._value.get())
    return result


async def get_metrics(
    session: AsyncSession,
    user_repo: UserRepository,
    community_id: uuid.UUID,
    settings: Settings,
) -> MetricsResponse:
    """
    @brief Aggregate community, system, and WAF metrics.

    Combines Prometheus in-memory gauges/counters with DB counts.
    @param session Async DB session.
    @param user_repo User repository for counts.
    @param community_id Community scope.
    @param settings Application config.
    @return Combined MetricsResponse.
    """
    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    users = await user_repo.count(community_id)
    users_active = await session.execute(
        select(func.count())
        .select_from(User)
        .where(
            User.community_id == community_id,
            User.deleted_at.is_(None),
            User.last_seen_at >= thirty_days_ago,
        ),
    )
    users_active_30d = users_active.scalar_one() or 0

    posts_total_stmt = (
        select(func.count())
        .select_from(Post)
        .where(
            Post.community_id == community_id,
            Post.deleted_at.is_(None),
        )
    )
    posts_total_result = await session.execute(posts_total_stmt)
    posts_total = posts_total_result.scalar_one() or 0

    posts_7d_stmt = select(func.count()).select_from(Post).where(
        Post.community_id == community_id,
        Post.deleted_at.is_(None),
        Post.created_at >= seven_days_ago,
    )
    posts_7d_result = await session.execute(posts_7d_stmt)
    posts_last_7d = posts_7d_result.scalar_one() or 0

    media_count_stmt = select(func.count()).select_from(Media).where(
        Media.community_id == community_id,
    )
    media_count_result = await session.execute(media_count_stmt)
    media_files = media_count_result.scalar_one() or 0

    media_storage_stmt = select(func.coalesce(func.sum(Media.size_bytes), 0)).where(
        Media.community_id == community_id,
    )
    media_storage_result = await session.execute(media_storage_stmt)
    media_storage_bytes = int(media_storage_result.scalar_one() or 0)

    users_online_now = _gauge_value(users_online)
    uptime_seconds = time.time() - _PROCESS_START_TIME
    blocks_by_reason = _counter_by_label(waf_blocks_total)
    blocks_today = sum(blocks_by_reason.values())
    celery_depth: int | None = _gauge_total(celery_queue_depth) or None

    return MetricsResponse(
        community=CommunityMetrics(
            users_total=users,
            users_active_30d=users_active_30d,
            users_online_now=users_online_now,
            posts_total=posts_total,
            posts_last_7d=posts_last_7d,
            media_files=media_files,
            media_storage_bytes=media_storage_bytes,
        ),
        system=SystemMetrics(
            version=settings.APP_VERSION,
            uptime_seconds=uptime_seconds,
            db_size_bytes=None,
            valkey_memory_bytes=None,
            celery_queue_depth=celery_depth,
        ),
        waf=WafMetrics(blocks_today=blocks_today, blocks_by_reason=blocks_by_reason),
    )
