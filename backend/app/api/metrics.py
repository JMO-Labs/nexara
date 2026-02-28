"""
@file metrics.py
@brief Prometheus ``/metrics`` endpoint.

Exposed **without authentication** — Prometheus scrapers cannot send auth
headers by default and the data is operational (counts, latencies) rather
than sensitive.  Users should restrict access at their reverse proxy.

The endpoint is mounted at the root (not under ``/api/v1/``) for the
conventional Prometheus scrape path.  In the Nginx config it is served
on a dedicated port ``:9090`` to simplify access control.
"""

from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

router = APIRouter()


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """
    @brief Prometheus metrics endpoint.

    Returns all registered metrics in the Prometheus text exposition format.
    Restrict access at your reverse proxy.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
