"""
@file admin_ai.py
@brief Admin endpoints for AI config, usage metrics and provider connection test.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.dependencies import get_admin_ai_service, require_role
from app.services.ai.admin_ai_service import AdminAIService

router = APIRouter(
    prefix="/admin/ai", tags=["admin-ai"], dependencies=[Depends(require_role("admin"))]
)


class AIConfigUpdate(BaseModel):
    """@brief Partial update of Sassybot settings."""

    sassybot_enabled: bool | None = None
    sass_level: int | None = Field(None, ge=1, le=3)
    probability: int | None = Field(None, ge=0, le=100)
    invoke_only: bool | None = None


@router.get("/config")
async def get_config(svc: AdminAIService = Depends(get_admin_ai_service)) -> dict[str, Any]:
    """@brief Current provider, Sassybot settings and opt-out count."""
    return await svc.get_config()


@router.put("/config")
async def put_config(
    body: AIConfigUpdate, svc: AdminAIService = Depends(get_admin_ai_service)
) -> dict[str, Any]:
    """@brief Update Sassybot settings (audit-logged)."""
    return await svc.update_config(body.model_dump(exclude_none=True))


@router.get("/metrics")
async def get_metrics(svc: AdminAIService = Depends(get_admin_ai_service)) -> dict[str, Any]:
    """@brief Daily usage, budget, 7-day series and per-feature breakdown."""
    return await svc.get_metrics()


@router.post("/test-connection")
async def test_connection(svc: AdminAIService = Depends(get_admin_ai_service)) -> dict[str, Any]:
    """@brief Probe the configured provider."""
    return await svc.test_connection()
