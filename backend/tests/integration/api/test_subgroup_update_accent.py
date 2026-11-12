"""
@file test_subgroup_update_accent.py
@brief Integration test for PUT /api/v1/subgroups/{slug} null-handling of updates.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user


class TestSubgroupUpdateAccent:
    """@brief PUT /subgroups/{slug} keeps explicit nulls only for nullable fields."""

    @pytest.mark.asyncio
    async def test_update_keeps_null_accent_and_parent_drops_other_nulls(self, test_app):
        """@brief accent_color/parent_id null are forwarded; other nulls are stripped."""
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

                transport = ASGITransport(app=test_app, raise_app_exceptions=False)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    # Response validation of the stub fails; only the call args matter.
                    await client.put(
                        "/api/v1/subgroups/family",
                        json={"accent_color": None, "parent_id": None, "description": None},
                    )

            _, _, updates = service.update_subgroup.call_args.args
            assert updates == {"accent_color": None, "parent_id": None}
        finally:
            test_app.dependency_overrides.clear()
