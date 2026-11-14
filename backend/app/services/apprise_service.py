"""@file apprise_service.py
@brief User-facing Apprise URL management (validation, ownership, test send).
"""

from __future__ import annotations

import uuid

import apprise

from app.core.exceptions import AppError, NotFoundError
from app.core.i18n import _
from app.models.apprise_url import AppriseURL
from app.repositories.apprise_repo import AppriseRepository


class AppriseService:
    """@brief Business rules over :class:`AppriseRepository`."""

    def __init__(self, repo: AppriseRepository, community_id: uuid.UUID) -> None:
        """@param repo Repository. @param community_id Tenant scope."""
        self._repo = repo
        self._community_id = community_id

    async def _owned(self, user_id: uuid.UUID, url_id: uuid.UUID) -> AppriseURL:
        row = await self._repo.get(url_id)
        if row is None or row.user_id != user_id or row.community_id != self._community_id:
            raise NotFoundError(_("Apprise URL not found"))
        return row

    async def list(self, user_id: uuid.UUID) -> list[AppriseURL]:
        """@brief All of the user's URLs (including disabled)."""
        return await self._repo.list_for_user(user_id, self._community_id, enabled_only=False)

    async def create(self, user_id: uuid.UUID, url: str, label: str | None) -> AppriseURL:
        """@brief Validate via Apprise, then store encrypted.

        @raises AppError 400 ``INVALID_APPRISE_URL`` if the URL does not parse.
        """
        try:
            valid = bool(apprise.Apprise().add(url))
        except Exception:
            valid = False
        if not valid:
            raise AppError(
                code="INVALID_APPRISE_URL",
                message=_("Invalid Apprise URL"),
                status_code=400,
            )
        row = await self._repo.create(self._community_id, user_id, url, label)
        return row

    async def update(
        self, user_id: uuid.UUID, url_id: uuid.UUID, label: str | None, enabled: bool | None
    ) -> AppriseURL:
        """@brief Update label and/or enabled flag of an owned URL."""
        row = await self._owned(user_id, url_id)
        if enabled is not None:
            await self._repo.set_enabled(url_id, enabled)
        if label is not None:
            await self._repo.set_label(url_id, label)
        refreshed = await self._repo.get(url_id)
        return refreshed or row

    async def delete(self, user_id: uuid.UUID, url_id: uuid.UUID) -> None:
        """@brief Delete an owned URL."""
        await self._owned(user_id, url_id)
        await self._repo.delete(url_id)

    async def test(self, user_id: uuid.UUID, url_id: uuid.UUID) -> tuple[bool, str]:
        """@brief Send a test notification to an owned URL."""
        await self._owned(user_id, url_id)
        return await self._repo.test_send(url_id, "Nexara test", "Test notification from Nexara")
