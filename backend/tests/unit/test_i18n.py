"""
@file test_i18n.py
@brief Unit tests for the i18n module.
"""

from app.core.i18n import _


class TestI18n:
    """@brief Verify the gettext wrapper returns strings correctly."""

    def test_passthrough_returns_same_string(self):
        """The fallback translator should return the input string unchanged."""
        assert _("Hello") == "Hello"

    def test_format_string_with_substitution(self):
        """The translator should support %-style string formatting."""
        result = _("Hello %(name)s") % {"name": "World"}
        assert result == "Hello World"

    def test_empty_string(self):
        """Empty strings should pass through without error."""
        assert _("") == ""

    def test_unicode_string(self):
        """Unicode strings should pass through correctly."""
        assert _("Ünïcödé") == "Ünïcödé"
