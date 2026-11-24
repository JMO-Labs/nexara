"""
@file scopes.py
@brief Allowlist mapping plugin-reachable API routes to the scope each requires.
"""

from __future__ import annotations

PLUGIN_ROUTE_SCOPES: dict[tuple[str, str], str] = {
    ("GET", "/api/v1/posts"): "posts:read",
    ("GET", "/api/v1/posts/{post_id}"): "posts:read",
    ("POST", "/api/v1/posts"): "posts:write",
    ("GET", "/api/v1/posts/{post_id}/comments"): "comments:read",
    ("POST", "/api/v1/posts/{post_id}/comments"): "comments:write",
    ("POST", "/api/v1/posts/{post_id}/reactions"): "reactions:write",
    ("POST", "/api/v1/posts/{post_id}/comments/{comment_id}/reactions"): "reactions:write",
    ("GET", "/api/v1/media/{media_id}"): "media:read",
    ("GET", "/api/v1/media/{media_id}/file"): "media:read",
    ("GET", "/api/v1/media/{media_id}/thumbnail"): "media:read",
    ("GET", "/api/v1/users/{user_id}"): "users:read",
    ("GET", "/api/v1/users/lookup"): "users:read",
}
"""@brief ``(METHOD, route template)`` -> required scope. Anything absent is denied."""
