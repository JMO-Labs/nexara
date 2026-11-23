"""
@file admin_email_service.py
@brief Admin view/update/test of SMTP settings. The password is write-only:
       stored encrypted, never returned.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.core.encryption import derive_fernet_key, encrypt_secret
from app.core.exceptions import NotFoundError
from app.repositories.community_repo import CommunityRepository
from app.services.email.sender import classify, send_email
from app.services.email.smtp_settings import config_from_env, config_from_row

# API field -> communities column (text fields only)
_TEXT = {
    "host": "smtp_host",
    "user": "smtp_user",
    "from_addr": "smtp_from",
    "from_name": "smtp_from_name",
}


class AdminEmailService:
    """@brief SMTP settings for the admin panel."""

    def __init__(
        self,
        communities: CommunityRepository,
        community_id: uuid.UUID,
        settings: Settings,
        audit_repo: Any | None = None,
        actor_id: uuid.UUID | None = None,
        ip_address: str | None = None,
    ) -> None:
        self._communities = communities
        self._cid = community_id
        self._settings = settings
        self._audit = audit_repo
        self._actor_id = actor_id
        self._ip = ip_address

    async def get(self) -> dict[str, Any]:
        """@return saved fields, has_password, configured and last status; no secrets."""
        c = await self._communities.get(self._cid)
        if c is None:
            raise NotFoundError()
        return {
            "host": c.smtp_host or "",
            "port": c.smtp_port or 587,
            "security": c.smtp_security or "starttls",
            "user": c.smtp_user or "",
            "from_addr": c.smtp_from or "",
            "from_name": c.smtp_from_name or "",
            "auth": c.smtp_auth or "password",
            "has_password": bool(c.smtp_password),
            "has_google_refresh": bool(c.smtp_google_refresh),
            "google_client_id": c.smtp_google_client_id or "",
            "has_google_client_secret": bool(c.smtp_google_client_secret),
            "google_env_client": bool(
                self._settings.GOOGLE_MAIL_CLIENT_ID and self._settings.GOOGLE_MAIL_CLIENT_SECRET
            ),
            "configured": bool(c.smtp_host),
            "last_ok_at": c.smtp_last_ok_at,
            "last_error": c.smtp_last_error,
        }

    async def update(self, changes: dict[str, Any]) -> dict[str, Any]:
        """
        @param changes host, port, security, user, password, from_addr, from_name, auth;
               '' clears a text field, a missing key keeps it
        """
        c = await self._communities.get(self._cid)
        if c is None:
            raise NotFoundError()
        values: dict[str, Any] = {}
        for key, col in _TEXT.items():
            if key in changes:
                values[col] = (changes[key] or "").strip() or None
        for key in ("port", "security", "auth"):
            if changes.get(key):
                values[f"smtp_{key}"] = changes[key]
        if "google_client_id" in changes:
            values["smtp_google_client_id"] = (changes["google_client_id"] or "").strip() or None
        if "google_client_secret" in changes:
            gs = (changes["google_client_secret"] or "").strip()
            values["smtp_google_client_secret"] = (
                encrypt_secret(gs, derive_fernet_key(self._settings.SECRET_KEY)) if gs else None
            )
        if "password" in changes:
            pw = (changes["password"] or "").strip()
            values["smtp_password"] = (
                encrypt_secret(pw, derive_fernet_key(self._settings.SECRET_KEY)) if pw else None
            )
        # Re-pointing the server or login must not carry the stored secrets to a new target.
        retarget = any(
            col in values and values[col] != getattr(c, col) for col in ("smtp_host", "smtp_user")
        ) or ("smtp_port" in values and values["smtp_port"] != (c.smtp_port or 587))
        # A refresh token is bound to the OAuth client that issued it.
        new_client = "smtp_google_client_id" in values and values["smtp_google_client_id"] != (
            c.smtp_google_client_id
        )
        if new_client:
            values["smtp_google_refresh"] = None
        if retarget:
            values["smtp_google_refresh"] = None
            if not (changes.get("password") or "").strip():
                values["smtp_password"] = None
        if await self._communities.update_smtp(self._cid, values) is None:
            raise NotFoundError()
        if self._audit is not None and values:
            await self._audit.append(
                actor_id=self._actor_id,
                action="email.settings.updated",
                target_type="community",
                target_id=self._cid,
                extra_data={"fields": sorted(changes)},  # never the values
                ip_address=self._ip,
            )
        return await self.get()

    async def test(self, to: str) -> dict[str, Any]:
        """
        @brief Send a test message with the saved settings (else env) and store the result.
        @param to Recipient address.
        @return ``{ok, error}``; error is truncated and free of secrets.
        """
        c = await self._communities.get(self._cid)
        if c is None:
            raise NotFoundError()
        cfg = config_from_row(c, self._settings.SECRET_KEY) or config_from_env(self._settings)
        if cfg is None:
            return {"ok": False, "error": "Save the mail server settings first.", "category": None}
        try:
            await send_email(
                cfg,
                to,
                "Nexara test email",
                "<p>Your Nexara email settings work.</p>",
                "Your Nexara email settings work.",
                record=False,
            )
        except Exception as exc:
            err = classify(exc)  # raw text is already in the server log
            await self._communities.update_smtp(self._cid, {"smtp_last_error": err.stored})
            return {"ok": False, "error": err.message, "category": err.category}
        await self._communities.update_smtp(
            self._cid, {"smtp_last_ok_at": datetime.now(UTC), "smtp_last_error": None}
        )
        return {"ok": True, "error": None, "category": None}
