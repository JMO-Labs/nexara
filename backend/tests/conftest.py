"""
@file conftest.py
@brief Shared pytest fixtures for all test modules.

Provides a session-scoped event loop. Database fixtures live in
tests/integration/ so unit tests run without external services.
"""

import asyncio

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """@brief Provide a single event loop for all session-scoped async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
