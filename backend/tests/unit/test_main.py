"""
@file test_main.py
@brief Unit tests for the FastAPI application factory and router setup.
"""

from app.main import app, create_app


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
        paths = [route.path for route in app.routes]
        assert "/healthz" in paths

    def test_metrics_route_registered(self):
        paths = [route.path for route in app.routes]
        assert "/metrics" in paths
