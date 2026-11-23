"""
@file email_reply_admin_service.py
@brief Admin view/update/test of reply-by-email (IMAP) settings.
       The mailbox password is write-only: stored encrypted, never returned.
"""

from __future__ import annotations

import asyncio
import imaplib
import uuid
from typing import Any

from app.core.config import Settings
from app.core.encryption import decrypt_secret, derive_fernet_key, encrypt_secret
from app.core.exceptions import NotFoundError
from app.repositories.community_repo import CommunityRepository
from app.services.email import imap_client
from app.services.email.reply_address import is_configured

_FIELDS = ("imap_host", "imap_user", "reply_address")


class EmailReplyAdminService:
    """@brief Reply-by-email settings for the admin panel."""

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
        """@return saved fields, has_password and configured; never the password."""
        c = await self._communities.get(self._cid)
        if c is None:
            raise NotFoundError()
        return {
            "imap_host": c.inbound_imap_host or "",
            "imap_port": c.inbound_imap_port or 993,
            "imap_user": c.inbound_imap_user or "",
            "reply_address": c.inbound_reply_address or "",
            "has_password": bool(c.inbound_imap_password),
            "configured": is_configured(c),
        }

    async def update(self, changes: dict[str, Any]) -> dict[str, Any]:
        """
        @param changes imap_host, imap_port, imap_user, imap_password, reply_address;
               '' clears a text field, a missing key keeps it
        """
        values: dict[str, Any] = {}
        for key in _FIELDS:
            if key in changes:
                name = "inbound_reply_address" if key == "reply_address" else f"inbound_{key}"
                values[name] = (changes[key] or "").strip() or None
        if changes.get("imap_port"):
            values["inbound_imap_port"] = int(changes["imap_port"])
        if "imap_password" in changes:
            pw = (changes["imap_password"] or "").strip()
            values["inbound_imap_password"] = (
                encrypt_secret(pw, derive_fernet_key(self._settings.SECRET_KEY)) if pw else None
            )
        if await self._communities.update_inbound(self._cid, values) is None:
            raise NotFoundError()
        if self._audit is not None and values:
            await self._audit.append(
                actor_id=self._actor_id,
                action="email_reply.updated",
                target_type="community",
                target_id=self._cid,
                extra_data={"fields": sorted(changes)},  # never the values
                ip_address=self._ip,
            )
        return await self.get()

    async def test(self) -> dict[str, Any]:
        """@brief Log in and select INBOX (nothing is read or deleted)."""
        c = await self._communities.get(self._cid)
        if c is None or not is_configured(c):
            return {"success": False, "message": "Fill in every field and save first."}
        password = decrypt_secret(
            c.inbound_imap_password or "", derive_fernet_key(self._settings.SECRET_KEY)
        )
        try:
            await asyncio.to_thread(
                imap_client.check,
                c.inbound_imap_host or "",
                c.inbound_imap_port,
                c.inbound_imap_user or "",
                password,
            )
        except imaplib.IMAP4.error:
            return {"success": False, "message": "The mail server refused the login."}
        except OSError:
            return {"success": False, "message": "Could not reach the mail server."}
        return {"success": True, "message": "Connected. The inbox can be read."}
