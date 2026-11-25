"""
@file plugin_deps.py
@brief FastAPI guards for plugin administration.
"""

from __future__ import annotations

from fastapi import Depends

from app.core.dependencies import get_current_user
from app.core.exceptions import AuthorizationError
from app.core.i18n import _
from app.models.user import COMMUNITY_DEFAULT, User


async def require_instance_owner(current_user: User = Depends(get_current_user)) -> User:
    """
    @brief Instance owner = human admin of the default community (plugin install/uninstall).
    @raises AuthorizationError For bots, non-admins and admins of other communities.
    """
    if (
        current_user.is_bot is True
        or current_user.role != "admin"
        or str(current_user.community_id) != COMMUNITY_DEFAULT
    ):
        raise AuthorizationError(message=_("Only the instance owner can do this"))
    return current_user
