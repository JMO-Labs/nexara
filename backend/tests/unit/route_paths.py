"""
@file route_paths.py
@brief Test helper: flatten an app's route paths across FastAPI versions.

FastAPI >= 0.16x stores ``include_router`` results as lazy ``_IncludedRouter``
wrappers in ``app.routes`` instead of copying the child routes.
"""

from typing import Any


def route_paths(app: Any) -> set[str]:
    """
    @brief Collect every effective route path registered on ``app``.
    @param app FastAPI/Starlette application or router.
    @return Set of path strings, including routes of included routers.
    """
    out: set[str] = set()
    for route in app.routes:
        expand = getattr(route, "effective_route_contexts", None)
        for ctx in expand() if callable(expand) else [route]:
            out.add(getattr(ctx, "path", ""))
    return out
