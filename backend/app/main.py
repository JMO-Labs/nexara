"""
@file main.py
@brief FastAPI application factory with lifespan, middleware stack, and router mounts.

Creates the FastAPI application instance used by Uvicorn.  Middleware is
registered in a specific order to ensure correct request processing:

  1. Request ID
  2. Structured Logging
  3. WAF
  4. CORS
  5. Rate Limiting
  6. Gzip
  7. Security Headers

Client IPs (incl. Cloudflare) are resolved by ``core.client_ip`` against
TRUSTED_PROXIES.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.metrics import router as metrics_router
from app.api.v1.health import router as health_router
from app.api.v1.router import api_v1_router, ws_api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    StructuredLoggingMiddleware,
)
from app.core.rate_limit import limiter
from app.core.valkey import DB_CACHE, close_pools, get_pool
from app.core.waf import WAFMiddleware
from app.db.session import async_session_factory, engine
from app.services.notifications import types as _notification_types  # noqa: F401

logger = structlog.get_logger(__name__)


def _configure_email_validator() -> None:
    """
    @brief Allow non-deliverable email domains (e.g. .local) in development.

    In production the default strict validation applies, rejecting
    domains that cannot receive mail.  In development we also remove
    ``local`` from the special-use blocklist so that LAN hostnames
    like ``user@mybox.local`` pass validation.
    """
    settings = get_settings()
    if settings.APP_ENV != "production":
        import email_validator

        email_validator.TEST_ENVIRONMENT = True
        blocked = email_validator.SPECIAL_USE_DOMAIN_NAMES
        if isinstance(blocked, list) and "local" in blocked:
            blocked.remove("local")


_configure_email_validator()


async def _seed_oauth_from_env(settings: Settings) -> None:
    """
    @brief Seed OAuth provider from OIDC_* env vars on first startup.

    If OIDC_ISSUER is set and no provider has been seeded yet,
    creates a default OIDC provider for the community.
    """
    import uuid

    if not settings.OIDC_ISSUER or not settings.OIDC_ISSUER.strip():
        return
    try:
        from app.services.oauth.provider_manager import ProviderManager

        async with async_session_factory() as session:
            manager = ProviderManager(session)
            await manager.seed_from_env(settings, uuid.UUID(settings.COMMUNITY_ID))
            await session.commit()
    except Exception:
        logger.warning("oauth_seed_from_env_failed", exc_info=True)


async def _seed_default_chat_channel(settings: Settings) -> None:
    """
    @brief Ensure every community has a default 'General' chat channel.

    Idempotent: checks for existence before creating. Runs on every startup
    to cover new communities added after initial migration.
    """
    import uuid

    try:
        from app.repositories.chat_repo import ChatChannelRepository

        async with async_session_factory() as session:
            chat_repo = ChatChannelRepository(session)
            community_id = uuid.UUID(settings.COMMUNITY_ID)
            await chat_repo.get_or_create_community_default(community_id)
            await session.commit()
    except Exception:
        logger.warning("seed_default_chat_channel_failed", exc_info=True)


def _warn_base_url(settings: Settings) -> None:
    """
    @brief Warn loudly when production runs on the default APP_BASE_URL.

    Email links would point at localhost:8000 and passkeys fail with an origin
    mismatch.

    @param settings Application settings.
    """
    if settings.APP_ENV == "production" and settings.base_url_unset:
        logger.warning(
            "app_base_url_unset",
            app_base_url=settings.APP_BASE_URL,
            hint="Set APP_BASE_URL to the URL members open (e.g. https://nexara.example.com); "
            "email links and passkeys depend on it.",
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    @brief Application startup / shutdown lifecycle.

    On startup: verify DB and Valkey connectivity, configure Prometheus.
    On shutdown: close connection pools cleanly.

    @param app The FastAPI application instance.
    """
    settings = get_settings()
    setup_logging(
        log_level=settings.LOG_LEVEL,
        json_output=settings.APP_ENV == "production",
    )
    logger.info(
        "app_starting",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
    )

    _warn_base_url(settings)
    await _seed_oauth_from_env(settings)
    await _seed_default_chat_channel(settings)

    from app.services.realtime.pubsub import start_subscriber, stop_subscriber

    await start_subscriber()
    logger.info("realtime_pubsub_subscriber_started")

    import asyncio

    from app.services.worker_watch import run_loop

    watchdog = asyncio.create_task(run_loop())

    yield

    watchdog.cancel()
    await stop_subscriber()
    await close_pools()
    await engine.dispose()
    logger.info("app_shutdown_complete")


def create_app() -> FastAPI:
    """
    @brief Build and configure the FastAPI application.

    @return Fully configured FastAPI instance ready for Uvicorn.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    _register_middleware(app, settings)
    _setup_instrumentator(app, settings)
    register_exception_handlers(app)
    _register_routers(app)

    return app


def _register_middleware(app: FastAPI, settings: Settings) -> None:
    """
    @brief Register the middleware stack in the correct order.

    Starlette middleware wraps in reverse registration order, so the first
    middleware to process a request must be registered **last**.
    We register bottom-up so the execution order is top-down:
      Request ID -> Logging -> WAF -> CORS -> Rate Limit -> Gzip -> Security Headers

    @param app The FastAPI application instance.
    @param settings Application settings.
    """
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]  # slowapi handler typed for RateLimitExceeded, not Exception
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    cache_client = None
    try:
        cache_client = get_pool(settings, DB_CACHE)
    except Exception:
        logger.warning("waf_cache_client_unavailable", exc_info=True)

    app.add_middleware(
        WAFMiddleware,  # type: ignore[arg-type]  # Starlette _MiddlewareFactory protocol vs class __init__
        settings=settings,
        cache_client=cache_client,
    )
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)


def _register_routers(app: FastAPI) -> None:
    """
    @brief Mount all API routers on the application.

    @param app The FastAPI application instance.
    """
    app.include_router(health_router, tags=["health"])
    app.include_router(api_v1_router)
    if get_settings().APP_ENV == "test":
        from app.api.v1._test import router as test_router

        app.include_router(test_router, prefix="/api/v1")
    app.include_router(ws_api_router)
    app.include_router(metrics_router)

    @app.get("/.well-known/jwks.json", tags=["auth"])
    async def jwks_root() -> dict[str, object]:
        """@brief Root-level JWKS endpoint for external JWT verification."""
        from app.core.security import get_jwks

        try:
            return get_jwks()
        except (PermissionError, OSError):
            logger.warning("jwks_key_unavailable", exc_info=True)
            return {"keys": []}


def _setup_instrumentator(app: FastAPI, settings: Settings) -> None:
    """
    @brief Configure prometheus-fastapi-instrumentator for auto HTTP metrics.

    Only activates when ``ENABLE_METRICS=true``.

    @param app The FastAPI application instance.
    @param settings Application settings.
    """
    if not settings.ENABLE_METRICS:
        return

    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/healthz", "/livez", "/metrics"],
    )
    instrumentator.instrument(app)


app = create_app()
"""@brief Module-level application instance for ``uvicorn app.main:app``."""
