"""
@file router.py
@brief Aggregates all v1 sub-routers into a single ``/api/v1`` prefix router.

New feature routers are added here as they are implemented across phases.
The health check router is **not** included here — it is mounted at the
root level (``/healthz``) in ``main.py`` for Docker HEALTHCHECK compatibility.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.invites import router as invites_router
from app.api.v1.sse import router as sse_router
from app.api.v1.users import router as users_router
from app.api.v1.ws import router as ws_router

api_v1_router = APIRouter(prefix="/api/v1")
"""@brief Top-level v1 API router mounted in ``main.py``."""

api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(invites_router)
api_v1_router.include_router(sse_router)

ws_api_router = ws_router
"""@brief WebSocket router mounted at root level (``/ws/``) in ``main.py``."""
