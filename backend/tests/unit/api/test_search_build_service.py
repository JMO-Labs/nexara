"""
@file test_search_build_service.py
@brief Unit tests for the search route's SearchService DI factory.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from app.api.v1.search import _build_service

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class TestBuildService:
    def test_uses_cache_pool_when_available(self):
        pool = MagicMock()
        with patch("app.api.v1.search.get_pool", return_value=pool) as gp:
            svc = _build_service(db=MagicMock(), community_id=CID, settings=MagicMock())
        gp.assert_called_once()
        assert svc._cache is pool
        assert svc._community_id == CID

    def test_falls_back_to_no_cache_when_pool_fails(self):
        with patch("app.api.v1.search.get_pool", side_effect=ConnectionError("down")):
            svc = _build_service(db=MagicMock(), community_id=CID, settings=MagicMock())
        assert svc._cache is None
