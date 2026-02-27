"""
@file router.py
@brief Aggregates all v1 sub-routers into a single ``/api/v1`` prefix router.

New feature routers are added here as they are implemented across phases.
The health check router is **not** included here — it is mounted at the
root level (``/healthz``) in ``main.py`` for Docker HEALTHCHECK compatibility.
"""

from fastapi import APIRouter

api_v1_router = APIRouter(prefix="/api/v1")
"""@brief Top-level v1 API router mounted in ``main.py``."""
