"""
@file test_list_dependencies.py
@brief Unit tests for the list service dependency providers.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.core import list_dependencies as deps
from app.services.list_completion_service import ListCompletionService
from app.services.list_items_service import ListItemService
from app.services.list_service import ListService
from app.services.list_signup_service import ListSignupService
from app.services.list_template_service import ListTemplateService
from app.services.notification_service import NotificationService

CID = uuid.uuid4()


def test_get_community_id_parses_settings() -> None:
    s = MagicMock()
    s.COMMUNITY_ID = str(CID)
    assert deps.get_community_id(s) == CID


def test_notifier_builds_service() -> None:
    assert isinstance(deps._notifier(MagicMock(), CID), NotificationService)


def test_service_providers_build_instances() -> None:
    db = MagicMock()
    assert isinstance(deps.get_list_service(db, CID), ListService)
    assert isinstance(deps.get_list_item_service(db, CID), ListItemService)
    assert isinstance(deps.get_list_completion_service(db, CID), ListCompletionService)
    assert isinstance(deps.get_list_signup_service(db, CID), ListSignupService)
    assert isinstance(deps.get_list_template_service(db), ListTemplateService)
