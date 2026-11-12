"""
@file test_subgroup_update.py
@brief Integration test for PUT /api/v1/subgroups/{slug} update filtering.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user


class TestSubgroupUpdateRoute:
    """@brief PUT /api/v1/subgroups/{slug} endpoint tests."""

    @pytest.mark.asyncio
    async def test_update_strips_none_but_keeps_nullable_fields(self, test_app):
        """@brief None values are dropped except parent_id/accent_color."""
        user = MagicMock()
        user.id = uuid.uuid4()

        async def _override_user():
            return user

        test_app.dependency_overrides[get_current_user] = _override_user
        try:
            with (
                patch("app.api.v1.subgroups.SubgroupService") as service_cls,
                patch("app.api.v1.subgroups._detail_response", new=AsyncMock(return_value={})),
            ):
                service = AsyncMock()
                service.update_subgroup = AsyncMock(return_value=MagicMock())
                service_cls.return_value = service

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    await client.put(
                        "/api/v1/subgroups/family",
                        json={"name": None, "accent_color": None, "parent_id": None},
                    )

            service.update_subgroup.assert_awaited_once()
            updates = service.update_subgroup.await_args.args[2]
            assert updates == {"accent_color": None, "parent_id": None}
        finally:
            test_app.dependency_overrides.clear()
