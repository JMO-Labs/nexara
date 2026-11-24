"""
@file admin_signins.py
@brief Admin: GET /admin/signins (paged log) and /admin/signins.csv (streamed export).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.deps_signins import get_admin_signin_service
from app.schemas.signin import SigninPage
from app.services.admin_signin_service import AdminSigninService

# Admin gate comes from get_admin_signin_service (require_role("admin")).
router = APIRouter(prefix="/admin", tags=["admin-signins"])


@router.get("/signins", response_model=SigninPage)
async def list_signins(
    q: str | None = Query(None, max_length=100),
    success: bool | None = None,
    method: str | None = None,
    since: datetime | None = None,
    cursor: str | None = None,
    svc: AdminSigninService = Depends(get_admin_signin_service),
) -> SigninPage:
    """@brief Filtered sign-in attempts, newest first (q matches email, IP, device)."""
    return await svc.list(q=q, success=success, method=method, since=since, cursor=cursor)


@router.get("/signins.csv")
async def export_signins(
    q: str | None = Query(None, max_length=100),
    success: bool | None = None,
    method: str | None = None,
    since: datetime | None = None,
    svc: AdminSigninService = Depends(get_admin_signin_service),
) -> StreamingResponse:
    """@brief Stream the filtered log as CSV (max 50 000 rows); audited."""
    body = await svc.export_csv(q=q, success=success, method=method, since=since)
    return StreamingResponse(
        body,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="signins.csv"'},
    )
