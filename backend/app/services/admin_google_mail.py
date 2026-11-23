"""
@file admin_google_mail.py
@brief "Connect Google account" flow for outgoing mail: state in Valkey, admin check, store.
"""

from __future__ import annotations

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

    async def start(self, admin_id: uuid.UUID) -> str:
        """@return Google consent URL; state is stored 10 minutes, single use."""
        client_id, _secret = await self._client()
        state = secrets.token_urlsafe(32)
        await self._vk.set(f"smtp:google_state:{state}", str(admin_id), ex=STATE_TTL)
        return build_auth_url(client_id, self.redirect_uri, state)

    async def complete(self, code: str, state: str) -> None:
        """
        @brief Verify state (consumed), check the initiator is still an admin, store tokens.
        @throws AuthorizationError bad/expired/used state or initiator no longer an admin
        """
        raw = await self._vk.getdel(f"smtp:google_state:{state}")
        if not raw:
            raise AuthorizationError(message=_("This connection link expired. Start again."))
        user = await self._users.get_by_id(uuid.UUID(str(raw)), self._cid)
        if user is None or user.role != "admin":
            raise AuthorizationError()
        client_id, secret = await self._client()
        refresh, email = await exchange_code(client_id, secret, self.redirect_uri, code)
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
