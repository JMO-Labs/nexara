"""
@file export_tasks.py
@brief Celery task for user data exports (generation lands in a follow-up).
"""

from __future__ import annotations

import structlog

from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.export_tasks.generate_user_export",
    queue="maintenance",
)
def generate_user_export(export_id: str) -> str:
    """@brief Placeholder: generate the export archive for ``export_id``."""
    logger.info("generate_user_export", export_id=export_id)
    return export_id
