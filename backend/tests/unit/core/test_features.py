"""
@file test_features.py
@brief Unit tests for per-community feature flag helpers.
"""

from unittest.mock import MagicMock

import pytest

from app.core.exceptions import AppError
from app.core.features import FEATURE_DEFAULTS, is_enabled, require_feature
from app.models.community import Community


def test_defaults_when_unset():
    c = MagicMock(spec=Community)
    c.features = {}
    assert is_enabled(c, "recipes") is True
    assert is_enabled(c, "reply_by_email") is False


def test_override_off():
    c = MagicMock(spec=Community)
    c.features = {"recipes": False}
    assert is_enabled(c, "recipes") is False
    with pytest.raises(AppError) as e:
        require_feature(c, "recipes")
    assert e.value.code == "FEATURE_DISABLED"
    assert e.value.status_code == 404


def test_unknown_key_raises_keyerror():
    with pytest.raises(KeyError):
        is_enabled(MagicMock(features={}), "nope")


def test_require_passes_when_on():
    c = MagicMock(spec=Community)
    c.features = None
    require_feature(c, "recap")


def test_defaults_has_all_keys():
    assert len(FEATURE_DEFAULTS) == 19
    assert [k for k, v in FEATURE_DEFAULTS.items() if not v] == ["reply_by_email"]
