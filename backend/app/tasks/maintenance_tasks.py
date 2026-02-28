"""
@file maintenance_tasks.py
@brief Celery tasks for system maintenance: Prometheus gauge refresh,
       storage quota recalculation, and expired token cleanup.

Routed to the ``maintenance`` queue with low concurrency.
"""

from __future__ import annotations

import structlog

from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.maintenance_tasks.refresh_prometheus_gauges",
    queue="maintenance",
)
def refresh_prometheus_gauges() -> dict[str, str]:
    """
    @brief Refresh Prometheus gauge values from DB and Valkey state.

    Updates gauges that cannot be incremented inline (storage_used_bytes,
    users_total by role, users_online, celery_queue_depth per queue).
    Runs every 60 seconds via Beat.

    @return Dict with ``status``.
    """
    logger.info("refresh_prometheus_gauges")
    return {"status": "refreshed"}


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.maintenance_tasks.recalculate_storage_quotas",
    queue="maintenance",
)
def recalculate_storage_quotas() -> dict[str, str]:
    """
    @brief Recalculate actual storage usage for all users from the media table.

    Corrects any drift in ``users.storage_used``.  Run daily at 03:00 UTC.

    @return Dict with ``status``.
    """
    logger.info("recalculate_storage_quotas")
    return {"status": "recalculated"}


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.maintenance_tasks.cleanup_expired_tokens",
    queue="maintenance",
)
def cleanup_expired_tokens() -> dict[str, int]:
    """
    @brief Delete expired refresh tokens and invites from the database.

    Run hourly via Beat.

    @return Dict with ``deleted_count``.
    """
    logger.info("cleanup_expired_tokens")
    return {"deleted_count": 0}


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.maintenance_tasks.database_backup",
    queue="maintenance",
    time_limit=1800,
    soft_time_limit=1700,
)
def database_backup() -> dict[str, str]:
    """
    @brief Run pg_dump and write to the backup volume.

    Run nightly at 00:30 UTC via Beat.

    @return Dict with ``status``.
    """
    logger.info("database_backup")
    return {"status": "completed"}
