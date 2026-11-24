"""
@file signin_log.py
@brief Sign-in event recording, new-device alerts and failure-burst detection.

Never stores the attempted password. Recording must never break login: use
:func:`record_signin_safe` from auth flows.
"""

from __future__ import annotations

import ipaddress
import re
import uuid
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.client_ip import client_ip
from app.core.config import Settings, get_settings
from app.core.valkey import DB_CACHE, get_pool
from app.db.session import async_session_factory
from app.models.signin_event import SigninEvent
from app.repositories.signin_repo import SigninRepository
from app.services.admin_alerts import admin_alert
from app.services.notifications.factory import build_notification_service

if TYPE_CHECKING:
    from fastapi import Request

    from app.models.user import User
    from app.services.notification_service import NotificationService

logger = structlog.get_logger(__name__)

BURST_THRESHOLD = 10
BURST_WINDOW_MINUTES = 10
_UA_MAX = 512

# Order matters: Edge UAs contain "Chrome"; Chrome UAs contain "Safari".
_BROWSERS = (
    ("Edge", re.compile(r"Edg(?:e|A|iOS)?/")),
    ("Firefox", re.compile(r"Firefox/|FxiOS/")),
    ("Chrome", re.compile(r"Chrome/|CriOS/")),
    ("Safari", re.compile(r"Safari/")),
)
# Order matters: iOS UAs contain "like Mac OS X"; Android UAs contain "Linux".
_OSES = (
    ("iOS", re.compile(r"iPhone|iPad|iPod")),
    ("Android", re.compile(r"Android")),
    ("Windows", re.compile(r"Windows")),
    ("macOS", re.compile(r"Macintosh|Mac OS X")),
    ("Linux", re.compile(r"Linux|X11")),
)


def parse_device(user_agent: str | None) -> str:
    """
    @brief Reduce a User-Agent to ``"{browser} on {os}"`` via a small regex table.

    @param user_agent Raw header value.
    @return Label, or ``"Unknown device"`` when browser or OS is unrecognised.
    """
    if not user_agent:
        return "Unknown device"
    browser = next((n for n, rx in _BROWSERS if rx.search(user_agent)), None)
    os_ = next((n for n, rx in _OSES if rx.search(user_agent)), None)
    return f"{browser} on {os_}" if browser and os_ else "Unknown device"


def _client_ip(request: Request | None) -> str | None:
    """@brief Real client IP (proxy-aware, as RefreshToken records it), validated."""
    host = client_ip(request) if request is not None else None
    if not host:
        return None
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        return None


async def _check_burst(
    session: AsyncSession,
    repo: SigninRepository,
    settings: Settings,
    community_id: uuid.UUID,
    ip: str,
) -> None:
    """@brief Log ``security.signin_burst`` once per 10 min per IP at >=10 failures."""
    if await repo.count_failures(community_id, ip, BURST_WINDOW_MINUTES) < BURST_THRESHOLD:
        return
    redis = get_pool(settings, DB_CACHE)
    if await redis.set(f"signin:burst:{ip}", "1", nx=True, ex=BURST_WINDOW_MINUTES * 60):
        logger.warning("security.signin_burst", ip=ip)
        await admin_alert(session, community_id, "signin_burst", {"ip": ip})


async def record_signin(
    session: AsyncSession,
    *,
    community_id: uuid.UUID,
    user_id: uuid.UUID | None,
    email: str | None,
    method: str,
    success: bool,
    reason: str | None,
    request: Request | None,
    notifier: NotificationService | None = None,
    settings: Settings | None = None,
) -> SigninEvent:
    """
    @brief Persist a sign-in event; alert on new device (success) or burst (failure).

    @param session DB session (event is flushed, not committed).
    @param community_id Community scope.
    @param user_id Resolved user, or None for unknown email.
    @param email Email typed by the user (lowercased, max 254 chars).
    @param method One of password/totp/recovery/passkey/magic_link/sso.
    @param success Whether the attempt succeeded.
    @param reason Failure reason code, or None.
    @param request Current request for IP / User-Agent (optional).
    @param notifier Override for the NotificationService (tests).
    @param settings Injected settings (defaults to ``get_settings()``).
    @return The stored SigninEvent.
    """
    repo = SigninRepository(session)
    ua = request.headers.get("user-agent") if request is not None else None
    ip = _client_ip(request)
    device = parse_device(ua)

    alert = False
    if success and user_id is not None:
        # Must be evaluated before the new row exists. First-ever login is not "new".
        alert = not await repo.has_success_with_device(
            community_id, user_id, device
        ) and await repo.has_any_success(community_id, user_id)

    event = await repo.add(
        SigninEvent(
            community_id=community_id,
            user_id=user_id,
            email_tried=(email.lower()[:254] if email else None),
            method=method,
            success=success,
            reason=reason,
            ip=ip,
            user_agent=ua[:_UA_MAX] if ua else None,
            device=device,
        )
    )

    try:
        if alert and user_id is not None:
            payload: dict[str, Any] = {
                "message": f"New sign-in from {device}",
                "device": device,
                "ip": ip,
            }
            svc = notifier or build_notification_service(session, community_id)
            await svc.notify(user_id, "new_signin", payload)
        elif not success and ip:
            await _check_burst(session, repo, settings or get_settings(), community_id, ip)
    except Exception:
        logger.warning("signin.alert_failed", exc_info=True)
    return event


async def record_signin_safe(session: AsyncSession, **kwargs: Any) -> SigninEvent | None:
    """
    @brief :func:`record_signin` that can never raise (runs in a SAVEPOINT).

    @return The event, or None after logging ``signin.record_failed``.
    """
    try:
        async with session.begin_nested():
            return await record_signin(session, **kwargs)
    except Exception:
        logger.warning("signin.record_failed", exc_info=True)
        return None


async def log_success(
    session: AsyncSession, settings: Settings, user: User, method: str, request: Request | None
) -> None:
    """@brief Safely record a successful sign-in for ``user``."""
    await record_signin_safe(
        session,
        community_id=user.community_id,
        user_id=user.id,
        email=user.email,
        method=method,
        success=True,
        reason=None,
        request=request,
        settings=settings,
    )


async def log_failure(
    settings: Settings,
    user: User | None,
    email: str | None,
    method: str,
    reason: str,
    request: Request | None = None,
    *,
    user_id: uuid.UUID | None = None,
) -> None:
    """
    @brief Safely record a failed sign-in in its OWN short-lived session.

    ``user_id`` names a known account when no ``User`` object is at hand.

    The caller is about to raise and ``get_db`` rolls back the request session, so
    the row is written and committed separately; no other pending request state
    is ever committed by this.
    """
    try:
        async with async_session_factory() as session:
            ev = await record_signin_safe(
                session,
                community_id=user.community_id if user else uuid.UUID(settings.COMMUNITY_ID),
                user_id=user.id if user else user_id,
                email=email,
                method=method,
                success=False,
                reason=reason,
                request=request,
                settings=settings,
            )
            if ev is not None:
                await session.commit()
    except Exception:
        logger.warning("signin.record_failed", exc_info=True)
