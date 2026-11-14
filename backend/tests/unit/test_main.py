"""
@file test_main.py
@brief Unit tests for the FastAPI application factory and router setup.
"""

from app.main import app, create_app
from tests.unit.route_paths import route_paths


class TestAppFactory:
    """@brief Verify the app is created with expected configuration."""

    def test_app_title(self):
        assert app.title == "Nexara"

    def test_app_version(self):
        assert app.version == "0.1.0"

    def test_create_app_returns_fastapi(self):
        from fastapi import FastAPI

        new_app = create_app()
        assert isinstance(new_app, FastAPI)


class TestRouteRegistration:
    """@brief Verify expected routes are registered on the app."""

    def test_healthz_route_registered(self):
        paths = route_paths(app)
        assert "/healthz" in paths

    def test_metrics_route_registered(self):
        paths = route_paths(app)
        assert "/metrics" in paths


class TestLoadPlugins:
    """@brief Plugin startup hook must never block startup."""

    async def test_failure_is_logged_not_raised(self, monkeypatch):
        from unittest.mock import MagicMock

        import app.main as main

        boom = MagicMock(side_effect=RuntimeError("db"))
        monkeypatch.setattr(main, "async_session_factory", boom)
        warn = MagicMock()
        monkeypatch.setattr(main.logger, "warning", warn)
        settings = MagicMock(COMMUNITY_ID="00000000-0000-0000-0000-000000000001")
        await main._load_plugins(main.app, settings)
        warn.assert_called_once()
        assert warn.call_args.args[0] == "plugins_load_failed"
