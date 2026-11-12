"""
@file admin_ai.py
@brief Admin endpoints for AI config, usage metrics and provider connection test.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_oauth import _client_ip, _community_id
from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role
from app.core.valkey import DB_CACHE, get_pool
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.services.ai.admin_ai_service import AdminAIService
from app.services.ai.budget_service import BudgetService
from app.services.ai.provider import get_ai_provider

router = APIRouter(
    prefix="/admin/ai", tags=["admin-ai"], dependencies=[Depends(require_role("admin"))]
)


class AIConfigUpdate(BaseModel):
    """@brief Partial update of Sassybot settings."""

    sassybot_enabled: bool | None = None
    sass_level: int | None = Field(None, ge=1, le=3)
    probability: int | None = Field(None, ge=0, le=100)
    invoke_only: bool | None = None


def get_admin_ai_service(
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    community_id: uuid.UUID = Depends(_community_id),
) -> AdminAIService:
    """@brief Build the service (admin only), with audit logging bound to the caller."""
    redis = get_pool(settings, DB_CACHE)

    async def audit(action: str, extra: dict[str, Any]) -> None:
        await AuditRepository(db).append(
            actor_id=user.id,
            action=action,
            target_type="community",
            target_id=community_id,
            extra_data=extra,
            ip_address=_client_ip(request),
        )

    budget = BudgetService(redis, settings.AI_DAILY_BUDGET_CENTS, settings.AI_BUDGET_RESET_HOUR)
    return AdminAIService(
        redis, db, community_id, settings, budget, lambda: get_ai_provider(settings), audit=audit
    )


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
