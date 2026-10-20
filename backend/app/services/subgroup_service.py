"""
@file subgroup_service.py
@brief Backwards-compatible shim re-exporting :class:`SubgroupService`.

The actual implementation lives in :mod:`app.services.subgroups` (split
across ``crud``, ``membership``, and ``pins`` modules to stay under the
400-line per-file limit).  This module is kept so existing imports of
``app.services.subgroup_service.SubgroupService`` continue to work.
"""

from __future__ import annotations

from app.services.subgroups import SubgroupService

__all__ = ["SubgroupService"]
