"""
@file deps_countdown.py
@brief DI for CountdownService (keeps repos out of routes).
"""

from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db
from app.core.list_dependencies import _notifier
from app.repositories.countdown_repo import CountdownRepository
from app.services.countdown_service import CountdownService


def get_countdown_service(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> CountdownService:
    """@brief CountdownService for the configured community."""
    cid = uuid.UUID(settings.COMMUNITY_ID)
    return CountdownService(CountdownRepository(db), cid, _notifier(db, cid))
