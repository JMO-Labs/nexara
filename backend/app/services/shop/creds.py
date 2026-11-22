"""
@file creds.py
@brief Resolve a community's Amazon credentials: admin-saved values
       (secret decrypted) first, server environment as the fallback.
"""

from __future__ import annotations

import uuid

from cryptography.fernet import InvalidToken

from app.core.config import Settings
from app.core.encryption import decrypt_secret, derive_fernet_key
from app.models.community import Community
from app.repositories.community_repo import CommunityRepository
from app.services.shop.amazon import Creds, creds_from


def saved_creds(community: Community | None, settings: Settings) -> dict[str, str | None]:
    """@brief Admin-saved values with the secret decrypted ('' if unreadable)."""
    if community is None:
        return {}
    secret = ""
    if community.amazon_client_secret:
        try:
            secret = decrypt_secret(
                community.amazon_client_secret, derive_fernet_key(settings.SECRET_KEY)
            )
        except InvalidToken:  # SECRET_KEY rotated: admin must re-enter it
            secret = ""
    return {
        "client_id": community.amazon_client_id,
        "client_secret": secret,
        "partner_tag": community.amazon_partner_tag,
        "marketplace": community.amazon_marketplace,
    }


async def creds_for(
    communities: CommunityRepository, community_id: uuid.UUID, settings: Settings
) -> Creds:
    """@brief Amazon credentials for one community."""
    return creds_from(settings, saved_creds(await communities.get(community_id), settings))
