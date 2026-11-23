"""
@file admin_google_mail.py
@brief "Connect Google account" flow for outgoing mail: state in Valkey, admin check, store.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import uuid
from typing import Any

from app.core.config import Settings
from app.core.encryption import derive_fernet_key, encrypt_secret
from app.core.exceptions import AppError, AuthorizationError
from app.core.i18n import _
from app.repositories.community_repo import CommunityRepository
from app.services.email.google_oauth import build_auth_url, client_credentials, exchange_code
from app.services.email.smtp_settings import config_from_row

STATE_TTL = 600
CALLBACK_PATH = "/api/v1/admin/email/google/callback"


def _hash(nonce: str) -> str:
    return hashlib.sha256(nonce.encode()).hexdigest()


class GoogleMailService:
    """@brief Start/complete the Google OAuth consent for the community's mail account."""

    def __init__(
        self,
        communities: CommunityRepository,
        users: Any,
        settings: Settings,
        valkey: Any,
    ) -> None:
        self._communities = communities
        self._users = users
        self._settings = settings
        self._vk = valkey
        self._cid = uuid.UUID(settings.COMMUNITY_ID)

    @property
    def redirect_uri(self) -> str:
        """@brief Callback URL registered in the Google OAuth client."""
        return self._settings.APP_BASE_URL.rstrip("/") + CALLBACK_PATH

    async def _client(self) -> tuple[str, str]:
        row = await self._communities.get(self._cid)
        cfg = config_from_row(row, self._settings.SECRET_KEY) if row is not None else None
        s = self._settings
        cid, secret = client_credentials(
            cfg.google_client_id if cfg else "",
            cfg.google_client_secret if cfg else "",
            s.GOOGLE_MAIL_CLIENT_ID,
            s.GOOGLE_MAIL_CLIENT_SECRET,
        )
        if not cid or not secret:
            raise AppError(
                code="GOOGLE_NOT_CONFIGURED",
                message=_("Enter a Google client ID and secret first."),
                status_code=409,
            )
        return cid, secret

    async def start(self, admin_id: uuid.UUID) -> tuple[str, str]:
        """
        @return (consent URL, browser nonce). The caller sets the nonce as an HttpOnly
                cookie; only its hash and the PKCE verifier are kept with the state.
        """
        client_id, _secret = await self._client()
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        record = {"uid": str(admin_id), "nh": _hash(nonce), "cv": verifier}
        await self._vk.set(f"smtp:google_state:{state}", json.dumps(record), ex=STATE_TTL)
        url = build_auth_url(client_id, self.redirect_uri, state, challenge.decode().rstrip("="))
        return url, nonce

    async def complete(self, code: str, state: str, nonce: str | None) -> None:
        """
        @brief Verify state (consumed) and browser nonce, check the initiator is still
               an admin, then store tokens.
        @throws AuthorizationError bad/expired/used state, wrong browser, or not an admin
        """
        raw = await self._vk.getdel(f"smtp:google_state:{state}")
        try:
            rec: dict[str, Any] = json.loads(raw) if raw else {}
            uid = uuid.UUID(rec["uid"])
            ok = bool(nonce) and secrets.compare_digest(rec["nh"], _hash(nonce or ""))
            verifier = str(rec["cv"])
        except (ValueError, TypeError, KeyError):
            ok = False
        if not ok:
            raise AuthorizationError(message=_("This connection link expired. Start again."))
        user = await self._users.get_by_id(uid, self._cid)
        if user is None or user.role != "admin":
            raise AuthorizationError()
        client_id, secret = await self._client()
        refresh, email = await exchange_code(client_id, secret, self.redirect_uri, code, verifier)
        key = derive_fernet_key(self._settings.SECRET_KEY)
        row = await self._communities.get(self._cid)
        # One direct write (not AdminEmailService.update) so the retarget rule that
        # drops the stored refresh token can't clear the one we just got.
        values: dict[str, Any] = {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_security": "starttls",
            "smtp_user": email,
            "smtp_auth": "google_oauth",
            "smtp_google_refresh": encrypt_secret(refresh, key),
            "smtp_password": None,
            "smtp_last_error": None,
        }
        if row is not None and not row.smtp_from:
            values["smtp_from"] = email
        await self._communities.update_smtp(self._cid, values)
