"""
@file link_previews.py
@brief Link preview API: fetch by ID, image proxy, admin manual scrape.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_role
from app.core.exceptions import AppError, NotFoundError
from app.core.i18n import _
from app.core.rate_limit import limiter
from app.models.link_preview import LinkPreview
from app.models.user import User
from app.repositories.link_preview_repo import LinkPreviewRepository
from app.schemas.link_preview import LinkPreviewResponse, ScrapeRequest, ScrapeResponse
from app.services.link_preview_service import fetch_image, is_safe_url
from app.tasks.link_preview_tasks import scrape_link_preview

router = APIRouter(prefix="/link-previews", tags=["link-previews"])

IMAGE_CACHE_SECONDS = 86400
"""@brief Browser cache lifetime for proxied images."""


def _get_repo(db: AsyncSession = Depends(get_db)) -> LinkPreviewRepository:
    """@brief Build the LinkPreviewRepository."""
    return LinkPreviewRepository(db)


async def _load(repo: LinkPreviewRepository, preview_id: uuid.UUID) -> LinkPreview:
    """@brief Fetch a preview or raise NotFoundError."""
    preview = await repo.get_by_id(preview_id)
    if preview is None:
        raise NotFoundError(_("Link preview not found"))
    return preview


@router.post("/scrape", response_model=ScrapeResponse, status_code=202)
@limiter.limit("10/minute")
async def scrape(
    request: Request,
    body: ScrapeRequest,
    _admin: User = Depends(require_role("admin")),
) -> ScrapeResponse:
    """@brief Admin-only manual scrape trigger; enqueues the Celery task."""
    if not is_safe_url(body.url):
        raise AppError(
            code="VALIDATION_ERROR",
            message=_("URL is not allowed"),
            status_code=422,
        )
    scrape_link_preview.delay(body.url)
    return ScrapeResponse(status="queued")


@router.get("/{preview_id}", response_model=LinkPreviewResponse)
async def get_preview(
    preview_id: uuid.UUID,
    response: Response,
    repo: LinkPreviewRepository = Depends(_get_repo),
) -> LinkPreviewResponse:
    """@brief Fetch a cached link preview by ID."""
    p = await _load(repo, preview_id)
    ttl = max(0, int((p.expires_at - datetime.now(UTC)).total_seconds()))
    response.headers["Cache-Control"] = f"public, max-age={min(ttl, IMAGE_CACHE_SECONDS)}"
    return LinkPreviewResponse(
        id=p.id,
        url=p.url,
        og_title=p.title,
        og_description=p.description,
        og_image=p.image_url,
        og_site_name=p.site_name,
        provider_type=p.provider_type,
        provider_id=p.provider_id,
        created_at=p.fetched_at,
        cache_ttl_seconds=ttl,
    )


@router.get("/{preview_id}/image")
@limiter.limit("60/minute")
async def get_preview_image(
    request: Request,
    preview_id: uuid.UUID,
    repo: LinkPreviewRepository = Depends(_get_repo),
) -> Response:
    """@brief Proxy the preview image so clients never contact third parties."""
    p = await _load(repo, preview_id)
    if not p.image_url:
        raise NotFoundError(_("Preview has no image"))
    fetched = await fetch_image(p.image_url)
    if fetched is None:
        raise NotFoundError(_("Preview image unavailable"))
    body, ctype = fetched
    return Response(
        content=body,
        media_type=ctype,
        headers={
            "Cache-Control": f"public, max-age={IMAGE_CACHE_SECONDS}",
            "X-Content-Type-Options": "nosniff",
        },
    )
