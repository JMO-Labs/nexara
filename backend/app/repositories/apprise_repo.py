"""@file apprise_repo.py
@brief CRUD for :class:`AppriseURL`; encrypts on write, decrypts on read.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import apprise
from sqlalchemy import select

from app.models.apprise_url import AppriseURL
from app.repositories.base import BaseRepository
from app.services.notifications.secrets import decrypt_url, encrypt_url

AUTO_DISABLE_THRESHOLD = 10


class AppriseRepository(BaseRepository[AppriseURL]):
    """@brief Async repository for Apprise URLs (community-scoped)."""

    model = AppriseURL

    async def create(  # type: ignore[override]
        self, community_id: uuid.UUID, user_id: uuid.UUID, url: str, label: str | None = None
    ) -> AppriseURL:
        """@brief Store a new URL encrypted.

        @return The row; ``apprise_url`` is the ciphertext.
        """
        row = AppriseURL(
            community_id=community_id,
            user_id=user_id,
            apprise_url=encrypt_url(url),
            label=label,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def list_for_user(
        self, user_id: uuid.UUID, community_id: uuid.UUID, *, enabled_only: bool = True
    ) -> list[AppriseURL]:
        """@brief A user's URLs (enabled only by default), ``apprise_url`` decrypted.

        Rows are detached from the session so the plaintext is never flushed.
        """
        stmt = select(AppriseURL).where(
            AppriseURL.user_id == user_id,
            AppriseURL.community_id == community_id,
        )
        if enabled_only:
            stmt = stmt.where(AppriseURL.enabled.is_(True))
        rows = list((await self._session.execute(stmt)).scalars().all())
        for r in rows:
            plain = decrypt_url(r.apprise_url)
            self._session.expunge(r)
            r.apprise_url = plain
        return rows

    async def get(self, url_id: uuid.UUID) -> AppriseURL | None:
        """@brief Fetch one row with ``apprise_url`` decrypted (detached)."""
        row = await self._session.get(AppriseURL, url_id)
        if row is None:
            return None
        plain = decrypt_url(row.apprise_url)
        self._session.expunge(row)
        row.apprise_url = plain
        return row

    async def record_success(self, url_id: uuid.UUID) -> None:
        """@brief Reset the failure counter."""
        row = await self._session.get(AppriseURL, url_id)
        if row is not None:
            row.failure_count = 0
            await self._session.flush()

    async def record_failure(self, url_id: uuid.UUID) -> int:
        """@brief Count a failure; disable at the threshold.

        @return New failure count (0 if the row is gone).
        """
        row = await self._session.get(AppriseURL, url_id)
        if row is None:
            return 0
        row.failure_count += 1
        row.last_failure_at = datetime.now(UTC)
        if row.failure_count >= AUTO_DISABLE_THRESHOLD:
            row.enabled = False
        await self._session.flush()
        return int(row.failure_count)

    async def set_enabled(self, url_id: uuid.UUID, enabled: bool) -> bool:
        """@brief Toggle a URL; re-enabling clears the failure counter.

        @return False if the row does not exist.
        """
        row = await self._session.get(AppriseURL, url_id)
        if row is None:
            return False
        row.enabled = enabled
        if enabled:
            row.failure_count = 0
        await self._session.flush()
        return True

    async def delete(self, url_id: uuid.UUID) -> bool:
        """@brief Hard-delete a URL. @return False if the row does not exist."""
        row = await self._session.get(AppriseURL, url_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.flush()
        return True

    async def test_send(self, url_id: uuid.UUID, title: str, body: str) -> tuple[bool, str]:
        """@brief Fire one notification at a URL; never raises, never leaks the URL.

        @return ``(ok, message)``.
        """
        row = await self.get(url_id)
        if row is None:
            return False, "URL not found"
        try:
            apobj = apprise.Apprise()
            if not apobj.add(row.apprise_url):
                return False, "Invalid Apprise URL"
            ok = await asyncio.to_thread(apobj.notify, body=body, title=title)
        except Exception as exc:
            return False, f"Delivery error: {type(exc).__name__}"
        return (True, "Test notification sent") if ok else (False, "Delivery failed")

    async def set_label(self, url_id: uuid.UUID, label: str) -> bool:
        """@brief Rename a URL. @return False if the row does not exist."""
        row = await self._session.get(AppriseURL, url_id)
        if row is None:
            return False
        row.label = label
        await self._session.flush()
        return True
