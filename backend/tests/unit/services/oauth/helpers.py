"""
@file helpers.py
@brief Shared OAuth provider mock with the SSO rule columns at their defaults.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock


def sso_provider(**overrides: Any) -> MagicMock:
    """
    @brief OAuthProvider mock: no domain/group gate, auto-create on, profile sync on.

    @param overrides Attributes to set (e.g. allowed_domains=["example.com"]).
    @return Provider mock.
    """
    p = MagicMock()
    p.id = uuid.uuid4()
    p.group_mappings = {}
    p.claim_mapping = {}
    p.allowed_domains = []
    p.required_group = None
    p.sync_profile = True
    p.auto_create_users = True
    p.preset = None
    p.username_claim = "preferred_username"
    for key, value in overrides.items():
        setattr(p, key, value)
    return p
