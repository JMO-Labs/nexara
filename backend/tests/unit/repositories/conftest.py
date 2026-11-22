"""@file conftest.py @brief Repository unit-test fixtures."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def _no_post_extras(request: pytest.FixtureRequest):
    """
    @brief enrich_posts tests script every session.execute call; the extra
           kudos/celebration lookups are covered in test_post_extras.py.
    """
    if request.node.module.__name__.endswith("test_post_extras"):
        yield
        return
    with patch("app.repositories.post_enrichment.post_extras", AsyncMock(return_value={})):
        yield
