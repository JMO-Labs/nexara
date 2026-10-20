"""
@file __init__.py
@brief Subgroup service package — re-exports :class:`SubgroupService`.

The package keeps per-concern modules (CRUD, membership, pinned posts)
small enough to stay under the 400-line per-file guideline.  External
callers should import :class:`SubgroupService` from this package (or
via the shim at :mod:`app.services.subgroup_service` for backwards
compatibility).
"""

from __future__ import annotations

from app.services.subgroups.service import SubgroupService

__all__ = ["SubgroupService"]
