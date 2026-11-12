"""
@file test_templates.py
@brief Unit tests for EmailTemplateRenderer.
"""

from __future__ import annotations

from app.services.email.templates import EmailTemplateRenderer


class TestTemplatesRender:
    """@brief Tests for template rendering."""

    def test_templates_render_with_branding_variables(self):
        """Templates render with community branding variables."""
        renderer = EmailTemplateRenderer()
        html, text = renderer.render(
            "notification.html",
            {"notification_type": "mention", "message": "You were mentioned"},
            community_name="TestCommunity",
            color_primary="#ff0000",
        )
        assert "TestCommunity" in html
        assert "#ff0000" in html
        assert "mention" in html.lower()
        assert "You were mentioned" in html
        assert "You were mentioned" in text

    def test_templates_produce_valid_html(self):
        """Templates produce valid HTML structure."""
        renderer = EmailTemplateRenderer()
        html, _ = renderer.render(
            "base.html",
            {},
            community_name="Nexara",
        )
        assert html.strip().startswith("<!DOCTYPE html>")
        assert "<html" in html
        assert "</html>" in html
        assert "<body" in html
        assert "</body>" in html


class TestFooterText:
    """@brief Footer text override in base template."""

    def test_footer_text_shown_when_set(self):
        html, _ = EmailTemplateRenderer().render("base.html", {}, footer_text="Custom footer line")
        assert "Custom footer line" in html
        assert "You received this email because" not in html

    def test_default_footer_when_unset(self):
        html, _ = EmailTemplateRenderer().render("base.html", {}, community_name="Acme")
        assert "You received this email because you have an account on Acme." in html
