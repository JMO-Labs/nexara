"""
@file router.py
@brief Aggregates all v1 sub-routers into a single ``/api/v1`` prefix router.

New feature routers are added here as they are implemented across phases.
The health check router is **not** included here — it is mounted at the
root level (``/healthz``) in ``main.py`` for Docker HEALTHCHECK compatibility.
"""

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.admin_oauth import router as admin_oauth_router
from app.api.v1.admin_plugins import router as admin_plugins_router
from app.api.v1.auth import router as auth_router
from app.api.v1.bookmarks import router as bookmarks_router
from app.api.v1.branding import router as branding_router
from app.api.v1.calendars import router as calendars_router
from app.api.v1.chat import router as chat_router
from app.api.v1.events import router as events_router
from app.api.v1.events import subs_router as calendar_subscriptions_router
from app.api.v1.galleries import router as galleries_router
from app.api.v1.home import router as home_router
from app.api.v1.interests import router as interests_router
from app.api.v1.invites import router as invites_router
from app.api.v1.kudos import router as kudos_router
from app.api.v1.media import router as media_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.nudges import router as nudges_router
from app.api.v1.oauth import router as oauth_router
from app.api.v1.oauth_admin import router as oauth_admin_router
from app.api.v1.polls import router as polls_router
from app.api.v1.posts import router as posts_router
from app.api.v1.prompts import router as prompts_router
from app.api.v1.push import router as push_router
from app.api.v1.search import router as search_router
from app.api.v1.settings import router as settings_router
from app.api.v1.sse import router as sse_router
from app.api.v1.subgroups import router as subgroups_router
from app.api.v1.users import router as users_router
from app.api.v1.ws import router as ws_router

api_v1_router = APIRouter(prefix="/api/v1")
"""@brief Top-level v1 API router mounted in ``main.py``."""

api_v1_router.include_router(admin_router)
api_v1_router.include_router(oauth_admin_router)
api_v1_router.include_router(admin_oauth_router)
api_v1_router.include_router(admin_plugins_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(oauth_router)
api_v1_router.include_router(branding_router)
api_v1_router.include_router(calendars_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(events_router)
api_v1_router.include_router(calendar_subscriptions_router)
api_v1_router.include_router(galleries_router)
api_v1_router.include_router(home_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(interests_router)
api_v1_router.include_router(invites_router)
api_v1_router.include_router(kudos_router)
api_v1_router.include_router(bookmarks_router)
api_v1_router.include_router(nudges_router)
api_v1_router.include_router(media_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(polls_router)
api_v1_router.include_router(posts_router)
api_v1_router.include_router(prompts_router)
api_v1_router.include_router(push_router)
api_v1_router.include_router(search_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(sse_router)
api_v1_router.include_router(subgroups_router)

ws_api_router = ws_router
"""@brief WebSocket router mounted at root level (``/ws/``) in ``main.py``."""
