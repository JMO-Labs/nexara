"""
@file test_search_build_service.py
@brief Unit tests for the search router's service factory.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from app.api.v1.search import _build_service

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_build_service_uses_cache_pool() -> None:
    pool = MagicMock()
    with patch("app.api.v1.search.get_pool", return_value=pool):
        svc = _build_service(db=MagicMock(), community_id=CID, settings=MagicMock())
    assert svc._cache is pool


def test_build_service_without_cache_when_pool_unavailable() -> None:
    with patch("app.api.v1.search.get_pool", side_effect=RuntimeError("no valkey")):
        svc = _build_service(db=MagicMock(), community_id=CID, settings=MagicMock())
    assert svc._cache is None
