"""
@file export_tasks.py
@brief Celery task for generating user data exports (``maintenance`` queue).
"""

from __future__ import annotations

import structlog

from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="app.tasks.export_tasks.generate_user_export")  # type: ignore[untyped-decorator]
def generate_user_export(export_id: str) -> dict[str, str]:
    """@brief Placeholder: generation is implemented in a follow-up ticket."""
    logger.info("user_export_requested", export_id=export_id)
    return {"export_id": export_id, "status": "pending"}
