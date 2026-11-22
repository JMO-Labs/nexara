"""
@file admin_shop.py
@brief Admin: Amazon Creators API settings for wishlist prices.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.dependencies import get_amazon_admin_service, require_role
from app.services.shop.amazon_admin_service import AmazonAdminService

router = APIRouter(
    prefix="/admin/shop", tags=["admin-shop"], dependencies=[Depends(require_role("admin"))]
)


class AmazonUpdate(BaseModel):
    """@brief Partial update; '' clears a field, an omitted field is kept."""

    client_id: str | None = Field(None, max_length=200)
    client_secret: str | None = Field(None, max_length=500)
    partner_tag: str | None = Field(None, max_length=100, pattern=r"^$|^[A-Za-z0-9_-]+$")
    marketplace: str | None = Field(None, pattern=r"^$|^www\.amazon\.[a-z]{2,3}(\.[a-z]{2})?$")


@router.get("/amazon")
async def get_amazon(svc: AmazonAdminService = Depends(get_amazon_admin_service)) -> dict[str, Any]:
    """@brief Saved settings (never the secret) and the source in use."""
    return await svc.get()


@router.put("/amazon")
async def put_amazon(
    body: AmazonUpdate, svc: AmazonAdminService = Depends(get_amazon_admin_service)
) -> dict[str, Any]:
    """@brief Save settings; the secret is encrypted at rest."""
    return await svc.update(body.model_dump(exclude_unset=True))


@router.post("/amazon/test")
async def test_amazon(
    svc: AmazonAdminService = Depends(get_amazon_admin_service),
) -> dict[str, Any]:
    """@brief Check the credentials against Amazon."""
    return await svc.test()
