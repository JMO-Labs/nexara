"""
@file test_notification_email_branding.py
@brief Branding is loaded and passed to the renderer by the email task.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.branding import CommunityBranding
from app.repositories.branding_repo import BrandingRepository
from app.tasks import notification_tasks as nt


def _patches(branding):
    session = AsyncMock()
    user = SimpleNamespace(email="a@b.c")
    session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=user))
    factory = MagicMock()
    factory.return_value.__aenter__.return_value = session
    repo = AsyncMock(spec=BrandingRepository)
    repo.get.return_value = branding
    renderer = MagicMock()
    renderer.render.return_value = ("<p>h</p>", "t")
    sender = MagicMock()
    sender.send = AsyncMock(return_value=True)
    return factory, repo, renderer, sender


async def _run(branding):
    factory, repo, renderer, sender = _patches(branding)
    with (
        patch.object(nt, "async_session_factory", factory),
        patch.object(nt, "BrandingRepository", return_value=repo),
        patch.object(nt, "EmailTemplateRenderer", return_value=renderer),
        patch.object(nt, "EmailSender", return_value=sender),
    ):
        await nt._send_email_notification_async(uuid.uuid4(), "comment", {})
    return renderer.render.call_args.kwargs


async def test_branding_passed_to_renderer():
    logo = uuid.uuid4()
    b = MagicMock(spec=CommunityBranding)
    b.community_name = "Acme"
    b.color_primary = "#112233"
    b.email_logo_media_id = logo
    b.logo_light_media_id = uuid.uuid4()
    b.email_footer_text = "Bye"
    kw = await _run(b)
    assert kw["community_name"] == "Acme"
    assert kw["color_primary"] == "#112233"
    assert kw["footer_text"] == "Bye"
    assert str(logo) in kw["logo_url"]


async def test_logo_falls_back_to_logo_light():
    light = uuid.uuid4()
    b = MagicMock(spec=CommunityBranding)
    b.community_name = "Acme"
    b.color_primary = "#112233"
    b.email_logo_media_id = None
    b.logo_light_media_id = light
    b.email_footer_text = None
    kw = await _run(b)
    assert str(light) in kw["logo_url"]
    assert kw["footer_text"] is None


async def test_no_branding_row_uses_defaults():
    kw = await _run(None)
    assert "community_name" not in kw
    assert "color_primary" not in kw
