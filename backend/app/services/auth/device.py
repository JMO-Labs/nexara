"""
@file device.py
@brief User-Agent to short device label helper (shared by sign-in log and push).
"""

from __future__ import annotations

import re

# Order matters: Edge UAs contain "Chrome"; Chrome UAs contain "Safari".
_BROWSERS = (
    ("Edge", re.compile(r"Edg(?:e|A|iOS)?/")),
    ("Firefox", re.compile(r"Firefox/|FxiOS/")),
    ("Chrome", re.compile(r"Chrome/|CriOS/")),
    ("Safari", re.compile(r"Safari/")),
)
# Order matters: iOS UAs contain "like Mac OS X"; Android UAs contain "Linux".
_OSES = (
    ("iOS", re.compile(r"iPhone|iPad|iPod")),
    ("Android", re.compile(r"Android")),
    ("Windows", re.compile(r"Windows")),
    ("macOS", re.compile(r"Macintosh|Mac OS X")),
    ("Linux", re.compile(r"Linux|X11")),
)


def parse_device(user_agent: str | None) -> str:
    """
    @brief Reduce a User-Agent to ``"{browser} on {os}"`` via a small regex table.

    @param user_agent Raw header value.
    @return Label, or ``"Unknown device"`` when browser or OS is unrecognised.
    """
    if not user_agent:
        return "Unknown device"
    browser = next((n for n, rx in _BROWSERS if rx.search(user_agent)), None)
    os_ = next((n for n, rx in _OSES if rx.search(user_agent)), None)
    return f"{browser} on {os_}" if browser and os_ else "Unknown device"
