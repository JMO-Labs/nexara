"""
@file test_user_provisioner.py
@brief Tests for UserProvisioner: OAuth user creation and linking.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.oauth_provider import OAuthProvider
from app.models.user import User
from app.models.user_oauth_link import UserOAuthLink
from app.services.oauth.user_provisioner import OAuthAuthResult, UserProvisioner


def _make_provider(
    provider_id: uuid.UUID | None = None,
    community_id: uuid.UUID | None = None,
) -> OAuthProvider:
    """@brief Create a mock OAuthProvider."""
    p = MagicMock(spec=OAuthProvider)
    p.id = provider_id or uuid.uuid4()
    p.community_id = community_id or uuid.UUID("00000000-0000-0000-0000-000000000001")
    p.group_mappings = {}
    p.default_role = "member"
    return p


def _make_auth_result(
    sub: str = "sub-123",
    email: str | None = "user@example.com",
    display_name: str | None = "Test User",
    avatar_url: str | None = None,
    groups: list[str] | None = None,
) -> OAuthAuthResult:
    """@brief Create OAuthAuthResult for tests."""
    return OAuthAuthResult(
        sub=sub,
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
        groups=groups or [],
        raw_claims={},
    )


class TestUserProvisionerNewUser:
    """@brief New user creation."""

    @pytest.mark.asyncio
    async def test_creates_user_and_link_when_no_existing(self):
        """@brief No user by sub or email -> creates User + UserOAuthLink."""
        community_id = uuid.uuid4()
        provider = _make_provider(community_id=community_id)
        auth = _make_auth_result(sub="new-sub", email="new@example.com", display_name="New User")

        created_user = MagicMock(spec=User)
        created_user.id = uuid.uuid4()
        created_user.community_id = community_id
        created_user.email = "new@example.com"
        created_user.role = "member"

        user_repo = AsyncMock(spec=["find_by_email", "find_by_username", "create", "update"])
        user_repo.find_by_email = AsyncMock(return_value=None)
        user_repo.find_by_username = AsyncMock(return_value=None)
        user_repo.create = AsyncMock(return_value=created_user)

        link_repo = AsyncMock(spec=["find_by_provider_and_sub", "create"])
        link_repo.find_by_provider_and_sub = AsyncMock(return_value=None)
        link_repo.create = AsyncMock(return_value=MagicMock())

        session = AsyncMock()
        provisioner = UserProvisioner(session, community_id)
        provisioner._user_repo = user_repo
        provisioner._link_repo = link_repo

        result = await provisioner.provision_user(auth, provider, "member")

        assert result == created_user
        link_repo.find_by_provider_and_sub.assert_called_once_with(provider.id, "new-sub")
        user_repo.find_by_email.assert_called_once_with("new@example.com")
        user_repo.create.assert_called_once()
        link_repo.create.assert_called_once()


class TestUserProvisionerLinkByEmail:
    """@brief Link existing user by email."""

    @pytest.mark.asyncio
    async def test_creates_link_and_updates_avatar_when_user_found_by_email(self):
        """@brief Existing user by email, no link -> creates UserOAuthLink, updates avatar."""
        community_id = uuid.uuid4()
        provider = _make_provider(community_id=community_id)
        auth = _make_auth_result(
            sub="link-sub",
            email="existing@example.com",
            display_name="Existing",
            avatar_url="https://idp.example.com/avatar.png",
        )

        existing_user = MagicMock(spec=User)
        existing_user.id = uuid.uuid4()
        existing_user.avatar_url = None

        link_repo = AsyncMock(spec=["find_by_provider_and_sub", "create"])
        link_repo.find_by_provider_and_sub = AsyncMock(return_value=None)
        link_repo.create = AsyncMock(return_value=MagicMock())

        user_repo = AsyncMock(spec=["find_by_email", "update", "create"])
        user_repo.find_by_email = AsyncMock(return_value=existing_user)
        user_repo.update = AsyncMock(return_value=existing_user)

        session = AsyncMock()
        provisioner = UserProvisioner(session, community_id)
        provisioner._user_repo = user_repo
        provisioner._link_repo = link_repo

        result = await provisioner.provision_user(auth, provider, "member")

        assert result == existing_user
        link_repo.create.assert_called_once()
        user_repo.update.assert_called()
        call_kwargs = user_repo.update.call_args
        assert call_kwargs[0][1].get("avatar_url") == "https://idp.example.com/avatar.png"


class TestUserProvisionerExistingLink:
    """@brief Existing link: update role and avatar."""

    @pytest.mark.asyncio
    async def test_updates_role_and_avatar_when_link_exists(self):
        """@brief UserOAuthLink found -> updates role, avatar if changed."""
        community_id = uuid.uuid4()
        provider = _make_provider(community_id=community_id)
        auth = _make_auth_result(
            sub="linked-sub",
            email="linked@example.com",
            avatar_url="https://idp.example.com/new-avatar.png",
        )

        existing_user = MagicMock(spec=User)
        existing_user.id = uuid.uuid4()
        existing_user.role = "member"
        existing_user.avatar_url = "https://old.com/avatar.png"

        existing_link = MagicMock(spec=UserOAuthLink)
        existing_link.user_id = existing_user.id

        link_repo = AsyncMock(spec=["find_by_provider_and_sub"])
        link_repo.find_by_provider_and_sub = AsyncMock(return_value=existing_link)

        user_repo = AsyncMock(spec=["get_by_id", "update"])
        user_repo.get_by_id = AsyncMock(return_value=existing_user)
        user_repo.update = AsyncMock(return_value=existing_user)

        session = AsyncMock()
        provisioner = UserProvisioner(session, community_id)
        provisioner._user_repo = user_repo
        provisioner._link_repo = link_repo

        result = await provisioner.provision_user(auth, provider, "admin")

        assert result == existing_user
        user_repo.update.assert_called()
        call_args = user_repo.update.call_args[0]
        assert call_args[1].get("role") == "admin"
        assert call_args[1].get("avatar_url") == "https://idp.example.com/new-avatar.png"


class TestUserProvisionerAvatarSync:
    """@brief Avatar sync behavior."""

    @pytest.mark.asyncio
    async def test_avatar_sync_when_provider_returns_avatar(self):
        """@brief Provider returns avatar_url -> user avatar updated."""
        community_id = uuid.uuid4()
        provider = _make_provider(community_id=community_id)
        auth = _make_auth_result(avatar_url="https://idp.example.com/photo.jpg")

        existing_link = MagicMock(spec=UserOAuthLink)
        existing_link.user_id = uuid.uuid4()
        link_repo = AsyncMock(spec=["find_by_provider_and_sub"])
        link_repo.find_by_provider_and_sub = AsyncMock(return_value=existing_link)

        existing_user = MagicMock(spec=User)
        existing_user.avatar_url = None
        user_repo = AsyncMock(spec=["get_by_id", "update"])
        user_repo.get_by_id = AsyncMock(return_value=existing_user)
        user_repo.update = AsyncMock(return_value=existing_user)

        session = AsyncMock()
        provisioner = UserProvisioner(session, community_id)
        provisioner._user_repo = user_repo
        provisioner._link_repo = link_repo

        await provisioner.provision_user(auth, provider, "member")

        user_repo.update.assert_called()
        assert (
            user_repo.update.call_args[0][1].get("avatar_url")
            == "https://idp.example.com/photo.jpg"
        )

    @pytest.mark.asyncio
    async def test_no_avatar_unchanged(self):
        """@brief Provider returns None for avatar -> user avatar unchanged."""
        community_id = uuid.uuid4()
        provider = _make_provider(community_id=community_id)
        auth = _make_auth_result(avatar_url=None)

        existing_link = MagicMock(spec=UserOAuthLink)
        existing_link.user_id = uuid.uuid4()
        link_repo = AsyncMock(spec=["find_by_provider_and_sub"])
        link_repo.find_by_provider_and_sub = AsyncMock(return_value=existing_link)

        existing_user = MagicMock(spec=User)
        existing_user.avatar_url = "https://existing.com/avatar.png"
        user_repo = AsyncMock(spec=["get_by_id", "update"])
        user_repo.get_by_id = AsyncMock(return_value=existing_user)
        user_repo.update = AsyncMock(return_value=existing_user)

        session = AsyncMock()
        provisioner = UserProvisioner(session, community_id)
        provisioner._user_repo = user_repo
        provisioner._link_repo = link_repo

        await provisioner.provision_user(auth, provider, "member")

        call_kwargs = user_repo.update.call_args[0][1]
        assert "avatar_url" not in call_kwargs or call_kwargs.get("avatar_url") is None


class TestUserProvisionerUsernameDerivation:
    """@brief Username derivation from name or email."""

    @pytest.mark.asyncio
    async def test_derives_username_from_name_or_email(self):
        """@brief Username derived from display_name or email."""
        community_id = uuid.uuid4()
        provider = _make_provider(community_id=community_id)
        auth = _make_auth_result(
            email="alice@example.com",
            display_name="Alice Smith",
        )

        created_user = MagicMock(spec=User)
        created_user.id = uuid.uuid4()

        link_repo = AsyncMock(spec=["find_by_provider_and_sub", "create"])
        link_repo.find_by_provider_and_sub = AsyncMock(return_value=None)
        link_repo.create = AsyncMock(return_value=MagicMock())

        user_repo = AsyncMock(spec=["find_by_email", "find_by_username", "create"])
        user_repo.find_by_email = AsyncMock(return_value=None)
        user_repo.find_by_username = AsyncMock(return_value=None)

        def check_create_call(entity):
            if hasattr(entity, "username"):
                assert entity.username == "Alice_Smith" or "alice" in entity.username.lower()
            return created_user

        user_repo.create = AsyncMock(side_effect=check_create_call)

        session = AsyncMock()
        provisioner = UserProvisioner(session, community_id)
        provisioner._user_repo = user_repo
        provisioner._link_repo = link_repo

        await provisioner.provision_user(auth, provider, "member")

        user_repo.create.assert_called_once()
        created_entity = user_repo.create.call_args[0][0]
        assert created_entity.username
        assert len(created_entity.username) <= 30
