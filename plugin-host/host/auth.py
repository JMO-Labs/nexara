"""
@file
@brief Bearer PLUGIN_HOST_SECRET check for control routes.
"""

import hmac

from fastapi import HTTPException, Request


def require_secret(request: Request) -> None:
    """
    @brief FastAPI dependency: constant-time bearer check against app.state.host.secret.
    @param request Incoming request.
    An empty configured secret rejects every request (fail closed).
    """
    secret: str = request.app.state.host.secret
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    ok = bool(secret) and scheme.lower() == "bearer"
    if not (hmac.compare_digest(token.encode(), secret.encode()) and ok):
        raise HTTPException(401, "unauthorized", headers={"WWW-Authenticate": "Bearer"})
