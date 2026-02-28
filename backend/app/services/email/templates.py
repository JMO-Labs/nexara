"""
@file templates.py
@brief Jinja2 email template renderer with branding context.

Loads templates from backend/templates/email/ and injects community branding.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates" / "email"
"""@brief Base path for email templates."""


class EmailTemplateRenderer:
    """
    @brief Renders email templates with Jinja2.

    Context includes community branding variables (community_name,
    color_primary, logo_url, etc.) for consistent styling.
    """

    def __init__(self, templates_dir: Path | None = None) -> None:
        """
        @brief Initialize the renderer.

        @param templates_dir Override templates directory; defaults to TEMPLATES_DIR.
        """
        base = templates_dir or TEMPLATES_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(base)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(
        self,
        template_name: str,
        context: dict[str, Any],
        *,
        community_name: str = "Nexara",
        color_primary: str = "#3b82f6",
        logo_url: str | None = None,
    ) -> tuple[str, str]:
        """
        @brief Render a template to HTML and plain text.

        Merges branding variables into context. Expects templates to
        produce HTML; plain text is derived by stripping tags (basic).

        @param template_name Template filename (e.g. notification.html).
        @param context Template variables.
        @param community_name Community display name.
        @param color_primary Primary brand color.
        @param logo_url Optional logo URL.
        @return Tuple of (html_body, text_body).
        """
        merged = {
            "community_name": community_name,
            "color_primary": color_primary,
            "logo_url": logo_url,
            **context,
        }
        template = self._env.get_template(template_name)
        html = template.render(**merged)

        import re

        text = re.sub(r"<[^>]+>", "", html)
        text = re.sub(r"\s+", " ", text).strip()
        return html, text
