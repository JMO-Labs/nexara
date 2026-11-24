"""@file admin_apprise_service.py
@brief Admin management of Apprise alert targets and the local-network opt-in.
"""

from __future__ import annotations

import uuid
from typing import Any

import apprise

from app.core.exceptions import AppError, NotFoundError
from app.core.i18n import _
from app.models.apprise_url import AppriseURL
from app.repositories.apprise_repo import AppriseRepository


class AdminAppriseService:
    """@brief Admin targets (community-level, never member-visible) with audit logging."""

    def __init__(
        self,
        repo: AppriseRepository,
        community_id: uuid.UUID,
        audit_repo: Any | None = None,
        actor_id: uuid.UUID | None = None,
        ip_address: str | None = None,
    ) -> None:
        self._repo = repo
        self._cid = community_id
        self._audit = audit_repo
        self._actor_id = actor_id
        self._ip = ip_address

    async def _log(self, action: str, target_id: uuid.UUID | None, extra: dict[str, Any]) -> None:
        if self._audit is not None:
            await self._audit.append(
                actor_id=self._actor_id,
                action=action,
                target_type="apprise_target",
                target_id=target_id,
                extra_data=extra,  # never the URL
                ip_address=self._ip,
            )

    async def _target(self, url_id: uuid.UUID) -> AppriseURL:
        row = await self._repo.get(url_id)
        if row is None or not row.is_admin_target or row.community_id != self._cid:
            raise NotFoundError(_("Apprise target not found"))
        return row

    async def list(self) -> list[AppriseURL]:
        """@brief All admin targets (including disabled)."""
        return await self._repo.list_admin_targets(self._cid, enabled_only=False)

    async def create(self, url: str, label: str | None) -> AppriseURL:
        """@brief Validate and store an admin target; local addresses are allowed."""
        try:
            valid = bool(apprise.Apprise().add(url))
        except Exception:
            valid = False
        if not valid:
            raise AppError(
                code="INVALID_APPRISE_URL", message=_("Invalid Apprise URL"), status_code=400
            )
        row = await self._repo.create(self._cid, None, url, label, is_admin_target=True)
        await self._log("apprise.target.created", row.id, {"label": label})
        return await self._repo.get(row.id) or row

    async def delete(self, url_id: uuid.UUID) -> None:
        """@brief Delete an admin target."""
        await self._target(url_id)
        await self._repo.delete(url_id)
        await self._log("apprise.target.deleted", url_id, {})

    async def test(self, url_id: uuid.UUID) -> tuple[bool, str]:
        """@brief Send a test alert to one admin target."""
        await self._target(url_id)
        ok, msg = await self._repo.test_send(url_id, "Nexara test", "Test alert from Nexara")
        await self._log("apprise.target.tested", url_id, {"ok": ok})
        return ok, msg

    async def allow_local(self) -> bool:
        """@brief Current member local-network opt-in."""
        return await self._repo.allow_local(self._cid)

    async def set_allow_local(self, value: bool) -> bool:
        """@brief Toggle whether members may target private/local hosts."""
        await self._repo.set_allow_local(self._cid, value)
        await self._log("apprise.settings.updated", None, {"allow_local": value})
        return value
