"""
@file google_oauth.py
@brief Google OAuth for mail (XOAUTH2): consent URL, code exchange, cached access tokens.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.valkey import DB_CACHE, create_pool
from app.services.email.smtp_settings import SmtpConfig

logger = structlog.get_logger(__name__)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
#: Mail scope plus the account email (read from the id_token at connect time).
SCOPE = "https://mail.google.com/ openid email"
_SKEW = 60


def _valkey() -> Redis:
    """@brief Fresh cache client (callers aclose it; Celery runs one loop per task)."""
    return create_pool(get_settings(), DB_CACHE)


def _http() -> httpx.AsyncClient:
    """@brief HTTP client for the token endpoint."""
    return httpx.AsyncClient(timeout=15)


def xoauth2_string(user: str, token: str) -> str:
    """@brief Base64 XOAUTH2 initial response (aiosmtplib builds the same in auth_xoauth2)."""
    return base64.b64encode(f"user={user}\x01auth=Bearer {token}\x01\x01".encode()).decode()


def client_credentials(
    client_id: str, client_secret: str, env_id: str, env_secret: str
) -> tuple[str, str]:
    """@brief Admin-entered client wins; env GOOGLE_MAIL_* is the fallback."""
    if client_id and client_secret:
        return client_id, client_secret
    return env_id, env_secret


def build_auth_url(client_id: str, redirect_uri: str, state: str, challenge: str) -> str:
    """@brief Google consent URL requesting a refresh token."""
    return AUTH_URL + "?" + urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )  # fmt: skip


async def _post_token(data: dict[str, str]) -> dict[str, Any] | None:
    """@brief POST to the token endpoint; None on a non-200 or non-JSON answer."""
    async with _http() as http:
        resp = await http.post(TOKEN_URL, data=data)
    if resp.status_code != 200:
        logger.warning("google_token_failed", status=resp.status_code)
        return None
    body = resp.json()
    return body if isinstance(body, dict) else None


def _id_token_email(id_token: str) -> str:
    """@brief Email claim of an id_token received straight from the token endpoint (TLS)."""
    payload = id_token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    return str(claims.get("email", ""))


async def exchange_code(
    client_id: str, client_secret: str, redirect_uri: str, code: str, code_verifier: str
) -> tuple[str, str]:
    """
    @brief Trade an authorization code for (refresh_token, google_email).
    @throws AppError 400 when Google refuses or returns no refresh token/email.
    """
    body = await _post_token(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
        }
    )
    refresh = (body or {}).get("refresh_token")
    email = _id_token_email(body["id_token"]) if body and body.get("id_token") else ""
    if not refresh or not email:
        raise AppError(
            code="GOOGLE_CONNECT_FAILED",
            message="Google did not return a usable sign-in. Try connecting again.",
            status_code=400,
        )
    return str(refresh), email


async def google_access_token(cfg: SmtpConfig) -> str:
    """
    @brief Access token for the connected Google account, cached in Valkey until expiry-60s.
    @throws SmtpSendError auth_failed when not connected or Google rejects the refresh token.
    """
    from app.services.email.sender import SmtpSendError  # sender imports this module

    if not cfg.google_refresh:
        raise SmtpSendError("auth_failed", "Google account is not connected.")
    s = get_settings()
    cid, secret = client_credentials(
        cfg.google_client_id,
        cfg.google_client_secret,
        s.GOOGLE_MAIL_CLIENT_ID,
        s.GOOGLE_MAIL_CLIENT_SECRET,
    )
    key = "smtp:google_at:" + hashlib.sha256(cfg.google_refresh.encode()).hexdigest()[:24]
    vk = _valkey()
    try:
        try:
            cached = await vk.get(key)
        except Exception:  # cache is an optimisation only
            cached = None
        if cached:
            return str(cached)
        body = await _post_token(
            {
                "client_id": cid,
                "client_secret": secret,
                "refresh_token": cfg.google_refresh,
                "grant_type": "refresh_token",
            }
        )
        token = (body or {}).get("access_token")
        if not token:
            raise SmtpSendError("auth_failed", "Google rejected the connection; reconnect it.")
        ttl = int((body or {}).get("expires_in", 3600)) - _SKEW
        if ttl > 0:
            try:
                await vk.set(key, token, ex=ttl)
            except Exception:
                logger.warning("google_token_cache_failed")
        return str(token)
    finally:
        await vk.aclose()
