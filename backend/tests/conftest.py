"""
@file conftest.py
@brief Shared pytest fixtures for all test modules.

Provides settings overrides, async database session fixtures (against a real
PostgreSQL test DB), and common test utilities.
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


@pytest.fixture(scope="session")
def event_loop():
    """@brief Provide a single event loop for all session-scoped async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """
    @brief Settings configured for the test environment.

    Uses a dedicated test database to avoid touching development data.
    Override DATABASE_URL via TEST_DATABASE_URL env var if needed.
    """
    return Settings(
        DATABASE_URL="postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
        SECRET_KEY="test-secret-key-not-for-production",
        DEBUG=True,
        STORAGE_BACKEND="local",
        LOCAL_STORAGE_PATH="/tmp/nexara_test_media",
        REDIS_URL="redis://127.0.0.1:6379",
    )


@pytest.fixture(scope="session")
async def async_engine(test_settings: Settings):
    """@brief Create an async engine pointing at the test database."""
    engine = create_async_engine(
        test_settings.DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=True,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def session_factory(async_engine) -> async_sessionmaker[AsyncSession]:
    """@brief Session factory bound to the test engine."""
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """
    @brief Provide a transactional database session for each test.

    Each test runs inside a transaction that is rolled back at the end,
    keeping the test database clean between tests.
    """
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()
