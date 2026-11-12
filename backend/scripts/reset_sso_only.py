#!/usr/bin/env python3
"""
@file reset_sso_only.py
@brief Emergency recovery: disable SSO-only mode (use if SSO provider is broken).

Usage: uv run python scripts/reset_sso_only.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.services.auth.sso_only import write_flag


async def main() -> None:
    """@brief Set sso_only=false for the default community."""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    async with async_sessionmaker(engine)() as session, session.begin():
        await write_flag(session, uuid.UUID(settings.COMMUNITY_ID), False, None)
    await engine.dispose()
    print("SSO-only mode disabled; password login restored.")


if __name__ == "__main__":
    asyncio.run(main())
