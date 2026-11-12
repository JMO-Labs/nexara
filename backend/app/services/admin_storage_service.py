"""
@file admin_storage_service.py
@brief Admin storage analytics: current usage, trend, per-user breakdown.
"""

from __future__ import annotations

import uuid

from app.models.user import User
from app.repositories.storage_repo import StorageRepository
from app.schemas.admin_storage import (
    StorageCurrent,
    StorageResponse,
    StorageSnapshotItem,
    UserStorageItem,
    UserStoragePage,
)

_TOP_USERS = 10


class AdminStorageService:
    """@brief Builds storage analytics payloads for admins."""

    def __init__(self, repo: StorageRepository, community_id: uuid.UUID) -> None:
        self._repo = repo
        self._community_id = community_id

    @staticmethod
    def _item(u: User, total: int) -> UserStorageItem:
        used = int(u.storage_used or 0)
        pct = round(used / total * 100, 1) if total > 0 else 0.0
        return UserStorageItem(
            user_id=u.id,
            display_name=u.display_name or u.username,
            used_bytes=used,
            percent_of_total=pct,
        )

    async def get_overview(self, days: int = 30) -> StorageResponse:
        """
        @brief Current usage, ``days`` of snapshots, and top users.
        @param days Trend window in days.
        @return StorageResponse
        """
        snaps = await self._repo.snapshots_since(days)
        if snaps:
            last = snaps[-1]
            current = StorageCurrent(
                total_bytes=last.total_bytes or 0,
                by_category={
                    "images": last.media_images_bytes or 0,
                    "videos": last.media_videos_bytes or 0,
                    "thumbnails": last.media_thumbnails_bytes or 0,
                    "other": last.media_other_bytes or 0,
                    "db": last.db_estimated_bytes or 0,
                },
            )
        else:
            current = StorageCurrent(
                total_bytes=0,
                by_category={k: 0 for k in ("images", "videos", "thumbnails", "other", "db")},
            )
        users = await self._repo.top_users(self._community_id, _TOP_USERS)
        total = await self._repo.total_user_bytes(self._community_id)
        return StorageResponse(
            current=current,
            snapshots=[
                StorageSnapshotItem(date=s.snapshot_date, total_bytes=s.total_bytes or 0)
                for s in snaps
            ],
            per_user=[self._item(u, total) for u in users],
        )

    async def list_users(self, page: int = 1, page_size: int = 100) -> UserStoragePage:
        """@brief Paginated per-user breakdown sorted by usage desc."""
        users, count = await self._repo.user_page(
            self._community_id, offset=(page - 1) * page_size, limit=page_size
        )
        total = await self._repo.total_user_bytes(self._community_id)
        return UserStoragePage(
            items=[self._item(u, total) for u in users],
            total=count,
            page=page,
            page_size=page_size,
        )
