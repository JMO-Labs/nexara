"""
@file newsletter.py
@brief Printable monthly newsletter: per-viewer read and admin pin/hide.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, require_role
from app.models.user import User
from app.schemas.newsletter import Newsletter, OverrideIn
from app.services.newsletter_service import NewsletterService

router = APIRouter(tags=["newsletter"])


def _build_service(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> NewsletterService:
    """@brief Build NewsletterService with injected dependencies."""
    return NewsletterService(db, uuid.UUID(settings.COMMUNITY_ID))


@router.get("/newsletter/{month}", response_model=Newsletter)
async def get_newsletter(
    month: str,
    user: User = Depends(get_current_user),
    service: NewsletterService = Depends(_build_service),
) -> Any:
    """@brief The newsletter for ``YYYY-MM`` as this viewer may see it."""
    return await service.build(month, user)


@router.put("/admin/newsletter/{month}/overrides", status_code=204)
async def put_override(
    month: str,
    body: OverrideIn,
    admin: User = Depends(require_role("admin")),
    service: NewsletterService = Depends(_build_service),
) -> Response:
    """@brief Pin or hide a post this month; ``action`` null clears it."""
    await service.set_override(month, admin, body.post_id, body.action)
    return Response(status_code=204)
