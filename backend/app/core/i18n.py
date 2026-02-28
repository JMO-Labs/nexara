"""
@file i18n.py
@brief Thin gettext wrapper for backend internationalization.

All user-facing strings (error messages, notification text, email templates)
are wrapped in ``_()`` from the first line of code.  Ships with ``en-US``
only; the community can contribute ``.po`` translations for other locales.

Usage::

    from app.core.i18n import _

    raise HTTPException(status_code=404, detail=_("Post not found"))
"""

import gettext
import os
from collections.abc import Callable

_locales_dir: str = os.path.join(os.path.dirname(__file__), "..", "..", "locales")
"""@brief Path to the ``locales/`` directory containing ``.mo`` files."""

_translation: gettext.NullTranslations = gettext.translation(
    "messages",
    _locales_dir,
    languages=["en_US"],
    fallback=True,
)
"""@brief Active translation catalogue (falls back to passthrough)."""

_: Callable[[str], str] = _translation.gettext
"""@brief Shorthand translator callable — ``_("some string")``."""
