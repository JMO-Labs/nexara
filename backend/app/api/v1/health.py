"""
@file health.py
@brief Health check endpoint for Docker HEALTHCHECK, load balancers, and admin dashboards.

Returns HTTP 200 when all critical components are healthy, HTTP 503 otherwise.
Component checks are non-blocking and fail independently.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db
from app.core.valkey import DB_CACHE, check_valkey_health, get_pool
from app.services.storage.factory import get_storage_backend

logger = structlog.get_logger(__name__)

router = APIRouter()


async def _check_db(db: AsyncSession) -> bool:
    """@brief Verify the database is reachable with a lightweight query."""
    try:
        await db.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.warning("healthz_db_check_failed", exc_info=True)
        return False


async def _check_redis(settings: Settings) -> bool:
    """@brief Verify Valkey is reachable via PING on the cache DB."""
    try:
        client = get_pool(settings, DB_CACHE)
        return await check_valkey_health(client)
    except Exception:
        logger.warning("healthz_redis_check_failed", exc_info=True)
        return False


async def _check_storage(settings: Settings) -> bool:
    """@brief Verify the configured storage backend is reachable."""
    try:
        backend = get_storage_backend(settings)
        return await backend.check_health()
    except Exception:
        logger.warning("healthz_storage_check_failed", exc_info=True)
        return False


@router.get("/healthz", include_in_schema=False)
async def healthz(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """
    @brief Returns component health status.

    HTTP 200 if all critical components (DB + Redis) are healthy.
    HTTP 503 if DB **or** Redis is unreachable (storage is non-critical).
    """
    checks = {
        "db": await _check_db(db),
        "redis": await _check_redis(settings),
        "storage": await _check_storage(settings),
    }
    all_critical = checks["db"] and checks["redis"]
    status = "healthy" if all_critical else "degraded"
    http_code = 200 if all_critical else 503

    return JSONResponse(
        status_code=http_code,
        content={
            "status": status,
            "version": settings.APP_VERSION,
            "checks": checks,
        },
    )


@router.get("/livez", include_in_schema=False)
async def livez() -> JSONResponse:
    """@brief Liveness probe; never touches DB, Valkey or storage."""
    return JSONResponse(status_code=200, content={"status": "alive"})
