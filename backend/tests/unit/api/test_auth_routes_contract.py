"""
@file test_auth_routes_contract.py
@brief Guards the public auth route table and file-size cap across router/service splits.
"""

from __future__ import annotations

from pathlib import Path

from app.main import app

EXPECTED = {
    ("GET", "/api/v1/auth/config"),
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),
    ("POST", "/api/v1/auth/logout"),
    ("POST", "/api/v1/auth/2fa/enroll"),
    ("POST", "/api/v1/auth/2fa/verify"),
    ("POST", "/api/v1/auth/2fa/login"),
    ("POST", "/api/v1/auth/password-reset/request"),
    ("POST", "/api/v1/auth/password-reset/confirm"),
    ("GET", "/api/v1/auth/oidc/login"),
    ("GET", "/api/v1/auth/oidc/callback"),
    ("GET", "/api/v1/auth/.well-known/jwks.json"),
    ("POST", "/api/v1/auth/magic-link/request"),
    ("GET", "/api/v1/auth/magic-link/verify"),
}


def test_auth_openapi_paths_unchanged() -> None:
    """@brief Every /auth operation keeps its method and URL."""
    got = {
        (m.upper(), p)
        for p, ops in app.openapi()["paths"].items()
        if p.startswith("/api/v1/auth/")
        for m in ops
    }
    assert got == EXPECTED


def test_auth_modules_under_400_lines() -> None:
    """@brief Auth router/service files stay under the 400-line cap."""
    root = Path(__file__).resolve().parents[3] / "app"
    for rel in ("api/v1/auth.py", "services/auth_service.py"):
        assert len((root / rel).read_text().splitlines()) < 400, rel
