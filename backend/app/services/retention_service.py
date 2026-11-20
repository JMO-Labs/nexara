"""
@file retention_service.py
@brief Admin retention policies: stored rows merged over built-in defaults.

No migration seeds ``retention_policies``; GET never writes. Known keys with no
row are returned with defaults (stamped epoch ``updated_at``); PUT upserts.
The table is instance-wide, so there is no community scoping.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.core.exceptions import NotFoundError
from app.repositories.retention_repo import RetentionRepository
from app.schemas.admin_retention import RetentionPolicyOut, RetentionUpdate

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

# key -> (enabled, retention_days, delete_media_files); mirrors frontend POLICY_META.
DEFAULT_POLICIES: dict[str, tuple[bool, int | None, bool]] = {
    "chat_messages": (True, 365, False),
    "notifications": (True, 90, False),
    "soft_deleted_posts": (True, 30, False),
    "soft_deleted_media": (True, 30, False),
    "soft_deleted_users": (True, 30, False),
    "link_preview_cache": (True, 90, False),
    "audit_logs": (True, 365, False),
    "auth_tokens": (True, None, False),
    "ai_usage_logs": (True, 90, False),
    "orphaned_media": (True, 7, False),
    "post_media_age": (False, None, False),
    "post_age": (False, None, False),
}


class RetentionService:
    """@brief List and update retention policies."""

    def __init__(self, repo: RetentionRepository) -> None:
        self._repo = repo

    async def list_policies(self) -> list[RetentionPolicyOut]:
        """@return One entry per known key, stored values overriding defaults."""
        stored = {r.policy_key: r for r in await self._repo.list_all()}
        out: list[RetentionPolicyOut] = []
        for key, (enabled, days, media) in DEFAULT_POLICIES.items():
            row = stored.get(key)
            if row is not None:
                out.append(RetentionPolicyOut.model_validate(row))
            else:
                out.append(
                    RetentionPolicyOut(
                        policy_key=key,
                        enabled=enabled,
                        retention_days=days,
                        delete_media_files=media,
                        updated_at=_EPOCH,
                        updated_by=None,
                    )
                )
        return out

    async def update(
        self, key: str, body: RetentionUpdate, user_id: uuid.UUID
    ) -> RetentionPolicyOut:
        """
        @param key policy_key
        @param body New values
        @param user_id Acting admin
        @raises NotFoundError for an unknown key
        """
        if key not in DEFAULT_POLICIES:
            raise NotFoundError(f"Unknown retention policy: {key}")
        row = await self._repo.upsert(
            key, body.enabled, body.retention_days, body.delete_media_files, user_id
        )
        return RetentionPolicyOut.model_validate(row)
