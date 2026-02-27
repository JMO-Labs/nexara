"""
@file quota.py
@brief Storage quota enforcement for user uploads.

Provides pre-upload quota checks and atomic storage accounting
(increment on upload, decrement on delete). A periodic Celery task
should call ``recalculate_storage_used`` to correct any drift.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = structlog.get_logger(__name__)


class QuotaExceededError(Exception):
    """@brief Raised when an upload would exceed the user's storage quota."""

    def __init__(self, quota: int, used: int, upload_size: int) -> None:
        self.quota = quota
        self.used = used
        self.upload_size = upload_size
        quota_gb = quota / (1024**3)
        super().__init__(
            f"Upload of {upload_size} bytes would exceed "
            f"your {quota_gb:.1f}GB quota"
        )


async def check_quota(
    session: AsyncSession,
    user_id: uuid.UUID,
    upload_size: int,
) -> None:
    """
    @brief Verify that the user has enough quota headroom for an upload.

    Reads the current ``storage_used`` and ``storage_quota`` from the
    users table and raises :class:`QuotaExceededError` if the upload
    would exceed the limit. Only original uploads count toward quota;
    thumbnails and transcoded files are free.

    @param session Active database session.
    @param user_id User attempting the upload.
    @param upload_size Size of the incoming file in bytes.
    @raises QuotaExceededError If quota would be exceeded.
    """
    result = await session.execute(
        select(User.storage_used, User.storage_quota).where(User.id == user_id)
    )
    row = result.one_or_none()
    if row is None:
        raise ValueError(f"User {user_id} not found")

    storage_used, storage_quota = row
    if storage_used + upload_size > storage_quota:
        raise QuotaExceededError(
            quota=storage_quota,
            used=storage_used,
            upload_size=upload_size,
        )


async def increment_storage_used(
    session: AsyncSession,
    user_id: uuid.UUID,
    size_bytes: int,
) -> None:
    """
    @brief Atomically increase a user's storage_used after a successful upload.

    Uses a SQL UPDATE with arithmetic to avoid race conditions
    when multiple uploads are in flight concurrently.

    @param session Active database session.
    @param user_id Owner of the uploaded file.
    @param size_bytes Size of the uploaded original in bytes.
    """
    await session.execute(
        text(
            "UPDATE users SET storage_used = storage_used + :size "
            "WHERE id = :user_id"
        ),
        {"size": size_bytes, "user_id": user_id},
    )
    logger.debug(
        "storage_used_incremented",
        user_id=str(user_id),
        added_bytes=size_bytes,
    )


async def decrement_storage_used(
    session: AsyncSession,
    user_id: uuid.UUID,
    size_bytes: int,
) -> None:
    """
    @brief Atomically decrease a user's storage_used after a file deletion.

    Clamps to zero to prevent negative values from rounding or
    double-delete edge cases.

    @param session Active database session.
    @param user_id Owner of the deleted file.
    @param size_bytes Size of the deleted original in bytes.
    """
    await session.execute(
        text(
            "UPDATE users "
            "SET storage_used = GREATEST(storage_used - :size, 0) "
            "WHERE id = :user_id"
        ),
        {"size": size_bytes, "user_id": user_id},
    )
    logger.debug(
        "storage_used_decremented",
        user_id=str(user_id),
        removed_bytes=size_bytes,
    )


async def recalculate_storage_used(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> int:
    """
    @brief Recalculate a user's actual storage usage from the media table.

    Queries the sum of ``size_bytes`` for all media uploaded by the user
    and updates ``storage_used`` to the true value. This corrects any
    drift from missed increments/decrements.

    Intended to be called by a periodic Celery task.

    @param session Active database session.
    @param user_id User whose usage to recalculate.
    @return The recalculated usage in bytes.
    """
    result = await session.execute(
        text(
            "SELECT COALESCE(SUM(size_bytes), 0) "
            "FROM media WHERE uploader_id = :user_id"
        ),
        {"user_id": user_id},
    )
    actual_usage: int = result.scalar_one()

    await session.execute(
        text("UPDATE users SET storage_used = :usage WHERE id = :user_id"),
        {"usage": actual_usage, "user_id": user_id},
    )
    logger.info(
        "storage_used_recalculated",
        user_id=str(user_id),
        actual_bytes=actual_usage,
    )
    return actual_usage
