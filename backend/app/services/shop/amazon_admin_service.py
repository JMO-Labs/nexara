"""
@file amazon_admin_service.py
@brief Admin view/update/test of a community's Amazon Creators API settings.
       The client secret is write-only: stored encrypted, never returned.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx

from app.core.config import Settings
from app.core.encryption import derive_fernet_key, encrypt_secret
from app.core.exceptions import NotFoundError
from app.repositories.community_repo import CommunityRepository
from app.services.shop import amazon
from app.services.shop.creds import saved_creds

TEST_ASIN = "B07FZ8S74R"  # a long-lived Amazon device listing


class AmazonAdminService:
    """@brief Amazon settings for the admin panel."""

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
        """@return saved fields, has_secret, and which source is in use."""
        community = await self._communities.get(self._cid)
        saved = saved_creds(community, self._settings)
        in_use = amazon.creds_from(self._settings, saved)
        admin = in_use.client_secret == saved.get("client_secret") and amazon.configured(in_use)
        return {
            "client_id": saved.get("client_id") or "",
            "partner_tag": saved.get("partner_tag") or "",
            "marketplace": saved.get("marketplace") or self._settings.AMAZON_MARKETPLACE,
            "has_secret": bool(community and community.amazon_client_secret),
            "source": "admin" if admin else ("server" if amazon.configured(in_use) else None),
        }

    async def update(self, changes: dict[str, str | None]) -> dict[str, Any]:
        """
        @param changes client_id, partner_tag, marketplace, client_secret;
               '' clears a field, a missing key keeps it
        """
        values: dict[str, str | None] = {}
        for key in ("client_id", "partner_tag", "marketplace"):
            if key in changes:
                values[f"amazon_{key}"] = (changes[key] or "").strip() or None
        if "client_secret" in changes:
            secret = (changes["client_secret"] or "").strip()
            values["amazon_client_secret"] = (
                encrypt_secret(secret, derive_fernet_key(self._settings.SECRET_KEY))
                if secret
                else None
            )
        if await self._communities.update_amazon(self._cid, values) is None:
            raise NotFoundError()
        if self._audit is not None and values:
            await self._audit.append(
                actor_id=self._actor_id,
                action="shop.amazon.updated",
                target_type="community",
                target_id=self._cid,
                extra_data={"fields": sorted(changes)},  # never the values
                ip_address=self._ip,
            )
        return await self.get()

    async def test(self) -> dict[str, Any]:
        """@brief Sign in to Amazon and look up one product."""
        c = amazon.creds_from(
            self._settings, saved_creds(await self._communities.get(self._cid), self._settings)
        )
        if not amazon.configured(c):
            return {"success": False, "message": "Add the client ID, secret and tracking ID."}
        try:
            async with httpx.AsyncClient(timeout=8.0, trust_env=False) as client:
                await amazon.access_token(client, c)
        except (httpx.HTTPError, ValueError, KeyError):
            return {"success": False, "message": "Amazon refused the client ID or secret."}
        if not await amazon.lookup([TEST_ASIN], c):
            return {
                "success": False,
                "message": "Signed in, but Amazon returned no products. "
                "Check the tracking ID and marketplace.",
            }
        return {"success": True, "message": "Connected. Amazon returned product data."}
