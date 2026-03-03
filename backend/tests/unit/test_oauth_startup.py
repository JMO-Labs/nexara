"""
@file test_oauth_startup.py
@brief Unit tests for OAuth startup seeding.

Verifies that seed_from_env is called when OIDC env vars are set.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_seed_from_env_called_when_oidc_configured():
    """ProviderManager.seed_from_env is called during app startup when OIDC vars set."""
    with patch("app.main._seed_oauth_from_env", new_callable=AsyncMock) as mock_seed:
        from app.main import create_app, lifespan

        app = create_app()
        async with lifespan(app):
            pass

        mock_seed.assert_called_once()
