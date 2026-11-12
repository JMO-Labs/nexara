"""
@file export_tasks.py
@brief Celery task that builds a user's data-export ZIP.
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.repositories.export_data_repo import ExportDataRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.user_export_repo import UserExportRepository
from app.services.export_service import build_export_archive
from app.services.notification_service import NotificationService
from app.services.storage.factory import get_storage_backend
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)

EXPORT_TTL = timedelta(hours=48)


def _notifier(session: AsyncSession, community_id: uuid.UUID) -> NotificationService:
    return NotificationService(
        notification_repo=NotificationRepository(session),
        settings_repo=SettingsRepository(session),
        community_id=community_id,
    )


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.export_tasks.generate_user_export",
    queue="default",
    time_limit=3600,
)
def generate_user_export(user_id: str, export_id: str) -> str:
    """@brief Build, store and announce the export archive for ``export_id``."""
    asyncio.run(_generate(user_id, export_id))
    return export_id


async def _generate(user_id: str, export_id: str) -> None:
    uid, eid = uuid.UUID(user_id), uuid.UUID(export_id)
    async with async_session_factory() as session:
        exports = UserExportRepository(session)
        export = await exports.get_by_id(eid)
        if export is None:
            logger.warning("export_missing", export_id=export_id)
            return
        notifier = _notifier(session, export.community_id)
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)  # noqa: SIM115
        try:
            await exports.update_status(eid, "processing")
            await session.commit()
            storage = get_storage_backend(get_settings())
            with tmp:
                await build_export_archive(ExportDataRepository(session), storage, uid, tmp)
            key = f"exports/{uid}/{eid}.zip"
            path = Path(tmp.name)
            await storage.put(key, path.read_bytes(), "application/zip")
            now = datetime.now(UTC)
            expires = now + EXPORT_TTL
            await exports.update_status(
                eid,
                "ready",
                file_key=key,
                file_size_bytes=path.stat().st_size,
                ready_at=now,
                expires_at=expires,
            )
            await notifier.notify(
                user_id=uid,
                type="data_export_ready",
                payload={
                    "export_id": export_id,
                    "expires_at": expires.isoformat(),
                    "download_url": f"/api/v1/export/{export_id}/download",
                },
            )
        except Exception as exc:
            logger.exception("export_failed", export_id=export_id)
            await session.rollback()
            await exports.update_status(eid, "failed", error_message=str(exc))
            await notifier.notify(
                user_id=uid, type="data_export_failed", payload={"export_id": export_id}
            )
        finally:
            Path(tmp.name).unlink(missing_ok=True)
        await session.commit()
