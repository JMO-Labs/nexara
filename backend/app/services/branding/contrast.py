"""
@file contrast.py
@brief WCAG contrast ratio and relative luminance utilities.
"""

from __future__ import annotations

import re

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """@brief Convert #RRGGBB to sRGB values (0-255)."""
    hex_color = hex_color.lstrip("#")
    return (
        float(int(hex_color[0:2], 16) / 255.0),
        float(int(hex_color[2:4], 16) / 255.0),
        float(int(hex_color[4:6], 16) / 255.0),
    )


def _linearize(c: float) -> float:
    """@brief Convert sRGB component to linear luminance."""
    if c <= 0.03928:
        return c / 12.92
    return float(((c + 0.055) / 1.055) ** 2.4)


def relative_luminance(hex_color: str) -> float:
    """
    @brief Compute relative luminance (WCAG 2.1).

    @param hex_color 6-digit hex string (#RRGGBB).
    @return Luminance in [0, 1].
    """
    if not _HEX_COLOR_RE.match(hex_color):
        msg = f"Invalid hex color: {hex_color}"
        raise ValueError(msg)
    r, g, b = _hex_to_rgb(hex_color)
    r_lin = _linearize(r)
    g_lin = _linearize(g)
    b_lin = _linearize(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(color1: str, color2: str) -> float:
    """
    @brief Compute contrast ratio (WCAG 2.1).

    @param color1 First hex color.
    @param color2 Second hex color.
    @return Contrast ratio (1.0 to 21.0).
    """
    l1 = relative_luminance(color1)
    l2 = relative_luminance(color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)
