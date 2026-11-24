"""
@file test_base_url_config.py
@brief APP_BASE_URL drives WebAuthn defaults; unset in production warns at startup.
"""

from unittest.mock import patch

from app.core.config import DEFAULT_BASE_URL, Settings
from app.main import _warn_base_url


def test_empty_base_url_falls_back_to_default():
    s = Settings(SECRET_KEY="t", APP_BASE_URL="")
    assert s.APP_BASE_URL == DEFAULT_BASE_URL and s.base_url_unset


def test_webauthn_defaults_cover_base_url_and_allowed_origins():
    s = Settings(
        SECRET_KEY="t",
        APP_BASE_URL="http://localhost:8090/",
        ALLOWED_ORIGINS="http://192.168.1.2:8090, http://localhost:8090,*",
    )
    assert s.webauthn_rp_id == "localhost"
    assert s.webauthn_origins == ["http://localhost:8090", "http://192.168.1.2:8090"]
    assert not s.base_url_unset


def test_explicit_webauthn_origin_wins():
    s = Settings(
        SECRET_KEY="t", APP_BASE_URL="https://a.example", WEBAUTHN_ORIGIN="https://b.example"
    )
    assert s.webauthn_origins == ["https://b.example"]


def test_startup_warns_only_in_production_with_default_url():
    with patch("app.main.logger") as log:
        _warn_base_url(Settings(SECRET_KEY="t", APP_ENV="production"))
        assert log.warning.call_args.args[0] == "app_base_url_unset"
        log.reset_mock()
        _warn_base_url(Settings(SECRET_KEY="t", APP_ENV="development"))
        _warn_base_url(
            Settings(SECRET_KEY="t", APP_ENV="production", APP_BASE_URL="https://x.example")
        )
        log.warning.assert_not_called()
