"""
@file test_plugins_desc.py
@brief Unit tests: plugin description helper only swallows expected errors.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.api.v1.plugins import _desc
from app.core.exceptions import NotFoundError, ValidationError
from app.services.plugin_service import PluginService


@pytest.mark.parametrize("exc", [NotFoundError(message="x"), ValidationError(message="x")])
def test_desc_returns_empty_on_expected_errors(exc: Exception) -> None:
    svc = MagicMock(spec=PluginService)
    svc.read_manifest.side_effect = exc
    assert _desc(svc, "p") == ""


def test_desc_propagates_unexpected_errors() -> None:
    svc = MagicMock(spec=PluginService)
    svc.read_manifest.side_effect = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        _desc(svc, "p")


def test_desc_returns_manifest_description() -> None:
    svc = MagicMock(spec=PluginService)
    svc.read_manifest.return_value.description = "hello"
    assert _desc(svc, "p") == "hello"
