"""
@file beat_lock.py
@brief PostgreSQL advisory lock for Celery Beat deduplication.

Celery Beat MUST only run as a single instance.  In Docker Compose this is
guaranteed by ``replicas: 1``, but in Kubernetes or multi-node setups a race
condition is possible.

Beat acquires a PostgreSQL advisory lock on startup.  If the lock is already
held by another Beat instance, this call **blocks** until the first one
releases it (on crash or shutdown).  PostgreSQL automatically releases the
lock when the connection drops.

Usage::

    from app.tasks.beat_lock import acquire_beat_lock

    acquire_beat_lock(database_url)  # blocks if another Beat holds the lock
    # ... start Beat scheduler ...
"""

from __future__ import annotations

import psycopg2
import structlog

logger = structlog.get_logger(__name__)

BEAT_LOCK_ID: int = 0xBEA7
"""@brief Arbitrary but stable advisory lock ID for Beat deduplication."""


def acquire_beat_lock(database_url: str) -> bool:
    """
    @brief Acquire a Postgres advisory lock for Beat.

    Blocks until the lock is acquired.  The lock is automatically released
    when the connection is closed (i.e. when the Beat process exits or crashes).

    @param database_url Synchronous PostgreSQL connection string
                        (e.g. ``postgresql://user:pass@host/db``).
    @return True when the lock has been acquired.
    @raises psycopg2.OperationalError On connection failure.
    """
    logger.info("beat_lock_acquiring", lock_id=BEAT_LOCK_ID)
    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("SELECT pg_advisory_lock(%s)", (BEAT_LOCK_ID,))
    logger.info("beat_lock_acquired", lock_id=BEAT_LOCK_ID)
    return True
