"""
@file test_branding_presets_api.py
@brief Route-level tests for branding preset endpoints.
"""

from __future__ import annotations

from app.api.v1.branding import router


def _routes() -> dict[tuple[str, str], object]:
    return {(m, r.path): r for r in router.routes for m in getattr(r, "methods", [])}


def test_presets_routes_registered():
    routes = _routes()
    assert ("GET", "/branding/presets") in routes
    assert ("POST", "/branding/presets/{theme_name}/apply") in routes
