"""
@file test_user_provisioner_hooks.py
@brief on_user_joined emission from OAuth provisioning (nexara#304).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.user import User
from app.services.oauth.user_provisioner import OAuthAuthResult, UserProvisioner

_P = "app.services.oauth.user_provisioner"


def _provisioner(link, new_user):
    link_repo = AsyncMock()
    link_repo.find_by_provider_and_sub.return_value = link
    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = None
    user_repo.create.return_value = new_user
    user_repo.get_by_id.return_value = new_user
    session = AsyncMock()
    cid = uuid.uuid4()
    with (
        patch(f"{_P}.UserOAuthLinkRepository", return_value=link_repo),
        patch(f"{_P}.UserRepository", return_value=user_repo),
        patch(f"{_P}.CalendarRepository", return_value=AsyncMock()),
    ):
        return UserProvisioner(session, cid), session, cid


def _provider():
    p = MagicMock()
    p.id = uuid.uuid4()
    p.group_mappings = None
    p.claim_mapping = None
    return p


async def test_new_oauth_user_emits_on_user_joined():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    prov, session, cid = _provisioner(None, user)
    auth = OAuthAuthResult(sub="s1", email="n@x.com", display_name="N", email_verified=True)
    with patch(f"{_P}.HookRegistry.emit", new=AsyncMock()) as emit:
        await prov.provision_user(auth, _provider(), "member")
    emit.assert_awaited_once_with(
        "on_user_joined", community_id=cid, session=session, user_id=user.id
    )


async def test_existing_linked_user_does_not_emit():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = "member"
    link = MagicMock()
    link.user_id = user.id
    link.avatar_url = None
    link.email_from_provider = "n@x.com"
    prov, _, _ = _provisioner(link, user)
    auth = OAuthAuthResult(sub="s1", email="n@x.com", display_name="N")
    with patch(f"{_P}.HookRegistry.emit", new=AsyncMock()) as emit:
        await prov.provision_user(auth, _provider(), "member")
    emit.assert_not_awaited()
