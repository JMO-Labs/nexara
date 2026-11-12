"""
@file test_search_build_service.py
@brief search._build_service tolerates an unavailable cache pool.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from app.api.v1.search import _build_service


def test_build_service_without_cache_when_pool_fails() -> None:
    with patch("app.api.v1.search.get_pool", side_effect=RuntimeError("no valkey")):
        svc = _build_service(MagicMock(), uuid.uuid4(), MagicMock())
    assert svc._cache is None
