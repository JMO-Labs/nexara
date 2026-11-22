"""
@file templates.py
@brief Jinja2 email template renderer with branding context.

Loads templates from backend/templates/email/ and injects community branding.
"""

from __future__ import annotations

import re
from html import unescape
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
        color_primary: str = "#24323D",
        logo_url: str | None = None,
        footer_text: str | None = None,
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
        @param footer_text Optional footer text replacing the default sentence.
        @return Tuple of (html_body, text_body).
        """
        merged = {
            "community_name": community_name,
            "color_primary": color_primary,
            "logo_url": logo_url,
            "footer_text": footer_text,
            **context,
        }
        template = self._env.get_template(template_name)
        html = template.render(**merged)

        return html, html_to_text(html)


def html_to_text(html: str) -> str:
    """
    @brief Plain-text alternative: drop head/style/script, keep block breaks,
           strip tags, unescape entities, collapse blank runs.
    """
    text = re.sub(r"<(head|style|script)\b.*?</\1>", "", html, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>|</(p|div|h[1-6]|li|tr|table|ul|ol)>", "\n", text, flags=re.I)
    text = unescape(re.sub(r"<[^>]+>", "", text))
    lines = (re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
