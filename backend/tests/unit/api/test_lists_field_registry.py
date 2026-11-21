"""
@file test_lists_field_registry.py
@brief Builtin list field types are registered on the app startup path.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
import uuid
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user

_SCRIPT = textwrap.dedent(
    """
    from app.main import create_app
    from app.services.list_field_registry import ListFieldRegistry
    create_app()
    reg = ListFieldRegistry()
    assert "text" in reg.keys(), reg.keys()
    reg.validate_config("text", {})
    """
)


def test_create_app_registers_builtin_field_types() -> None:
    """@brief Fresh interpreter: create_app() alone must populate the registry."""
    res = subprocess.run(  # noqa: S603
        [sys.executable, "-c", _SCRIPT], capture_output=True, text=True, timeout=120
    )
    assert res.returncode == 0, res.stderr[-2000:]


@pytest.fixture
async def client(test_app):
    user = SimpleNamespace(id=uuid.uuid4(), role="member", community_id=uuid.uuid4())
    test_app.dependency_overrides[get_current_user] = lambda: user
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        yield c
    test_app.dependency_overrides.clear()


async def test_field_types_route_not_captured_by_list_id(client) -> None:
    r = await client.get("/api/v1/lists/field-types")
    assert r.status_code == 200
    keys = {t["key"] for t in r.json()}
    assert {"text", "select", "date"} <= keys
