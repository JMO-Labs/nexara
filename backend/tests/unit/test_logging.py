"""
@file test_logging.py
@brief Unit tests for the structured logging configuration module.
"""

import logging

from app.core.logging import setup_logging


class TestSetupLogging:
    """@brief Verify logging configuration."""

    def test_setup_does_not_raise(self):
        setup_logging(log_level="DEBUG", json_output=False)

    def test_root_logger_has_handler(self):
        setup_logging(log_level="INFO", json_output=True)
        root = logging.getLogger()
        assert len(root.handlers) > 0

    def test_log_level_applied(self):
        setup_logging(log_level="WARNING", json_output=False)
        root = logging.getLogger()
        assert root.level == logging.WARNING
