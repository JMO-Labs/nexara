"""
@file test_user_provisioner.py
@brief Unit tests for OAuth user provisioning and linking.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthenticationError
from app.models.user import User
from app.services.oauth.user_provisioner import (
    OAuthAuthResult,
    UserProvisioner,
    _derive_username,
)


class TestDeriveUsername:
    """@brief Tests for _derive_username function."""

    def test_from_display_name_removes_spaces_and_special_chars(self):
        """_derive_username from display name removes spaces and special chars."""
        result = _derive_username("John Doe!", "j@x.com")
        assert result == "John_Doe"

    def test_from_email_uses_part_before_at(self):
        """_derive_username from email uses part before @."""
        result = _derive_username(None, "alice@example.com")
        assert result == "alice"

    def test_returns_fallback_when_both_none(self):
        """_derive_username returns fallback when both None."""
        result = _derive_username(None, None)
        assert result.startswith("user_")
        assert len(result) == len("user_") + 8

    def test_truncates_to_30_chars(self):
        """_derive_username truncates to 30 chars."""
        long_name = "a" * 50
        result = _derive_username(long_name, None)
        assert len(result) == 30
        assert result == "a" * 30


class TestProvisionUser:
    """@brief Tests for UserProvisioner.provision_user."""

    @pytest.mark.asyncio
    async def test_returns_existing_user_when_link_found(self):
        """provision_user returns existing user when link found."""
        mock_session = AsyncMock()
        mock_link_repo = AsyncMock()
        mock_user_repo = AsyncMock()

        mock_link = MagicMock()
        mock_link.user_id = uuid.uuid4()
        mock_link_repo.find_by_provider_and_sub = AsyncMock(return_value=mock_link)

        mock_user = MagicMock(spec=User)
        mock_user.id = mock_link.user_id
        mock_user.role = "member"
        mock_user.avatar_url = None
        mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)

        auth_result = OAuthAuthResult(sub="oidc-123", email="u@x.com", display_name="User")
        mock_provider = MagicMock()
        mock_provider.id = uuid.uuid4()

        with patch(
            "app.services.oauth.user_provisioner.UserOAuthLinkRepository",
            return_value=mock_link_repo,
        ):
            with patch(
                "app.services.oauth.user_provisioner.UserRepository",
                return_value=mock_user_repo,
            ):
                provisioner = UserProvisioner(mock_session, uuid.uuid4())
                result = await provisioner.provision_user(auth_result, mock_provider, "member")

        assert result is mock_user
        mock_link_repo.find_by_provider_and_sub.assert_called_once_with(
            mock_provider.id, "oidc-123"
        )

    @pytest.mark.asyncio
    async def test_updates_role_when_changed_existing_link(self):
        """provision_user updates role when changed (existing link)."""
        mock_session = AsyncMock()
        mock_link_repo = AsyncMock()
        mock_user_repo = AsyncMock()

        mock_link = MagicMock()
        mock_link.user_id = uuid.uuid4()
        mock_link_repo.find_by_provider_and_sub = AsyncMock(return_value=mock_link)

        mock_user = MagicMock(spec=User)
        mock_user.id = mock_link.user_id
        mock_user.role = "viewer"
        mock_user.avatar_url = None
        mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
        mock_user_repo.update = AsyncMock(return_value=mock_user)

        auth_result = OAuthAuthResult(sub="oidc-123", email="u@x.com")
        mock_provider = MagicMock()
        mock_provider.id = uuid.uuid4()

        with patch(
            "app.services.oauth.user_provisioner.UserOAuthLinkRepository",
            return_value=mock_link_repo,
        ):
            with patch(
                "app.services.oauth.user_provisioner.UserRepository",
                return_value=mock_user_repo,
            ):
                provisioner = UserProvisioner(mock_session, uuid.uuid4())
                await provisioner.provision_user(auth_result, mock_provider, "admin")

        mock_user_repo.update.assert_called_once_with(mock_user, {"role": "admin"})

    @pytest.mark.asyncio
    async def test_creates_link_when_user_found_by_email(self):
        """provision_user creates link when user found by email."""
        mock_session = AsyncMock()
        mock_link_repo = AsyncMock()
        mock_user_repo = AsyncMock()

        mock_link_repo.find_by_provider_and_sub = AsyncMock(return_value=None)
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid.uuid4()
        mock_user.avatar_url = None
        mock_user_repo.find_by_email = AsyncMock(return_value=mock_user)
        mock_user_repo.update = AsyncMock(return_value=mock_user)
        mock_link_repo.create = AsyncMock()

        auth_result = OAuthAuthResult(
            sub="oidc-456", email="existing@example.com",
            avatar_url="https://x.com/a.png",
            email_verified=True,
        )
        mock_provider = MagicMock()
        mock_provider.id = uuid.uuid4()

        with patch(
            "app.services.oauth.user_provisioner.UserOAuthLinkRepository",
            return_value=mock_link_repo,
        ):
            with patch(
                "app.services.oauth.user_provisioner.UserRepository",
                return_value=mock_user_repo,
            ):
                provisioner = UserProvisioner(mock_session, uuid.uuid4())
                result = await provisioner.provision_user(auth_result, mock_provider, "member")

        assert result is mock_user
        mock_link_repo.create.assert_called_once()
        call_args = mock_link_repo.create.call_args[0][0]
        assert call_args.user_id == mock_user.id
        assert call_args.provider_id == mock_provider.id
        assert call_args.sub == "oidc-456"

    @pytest.mark.asyncio
    async def test_creates_new_user_and_link_when_no_match(self):
        """provision_user creates new user and link when no match."""
        mock_session = AsyncMock()
        mock_link_repo = AsyncMock()
        mock_user_repo = AsyncMock()

        mock_link_repo.find_by_provider_and_sub = AsyncMock(return_value=None)
        mock_user_repo.find_by_email = AsyncMock(return_value=None)
        mock_user_repo.find_by_username = AsyncMock(return_value=None)

        new_user = MagicMock(spec=User)
        new_user.id = uuid.uuid4()
        mock_user_repo.create = AsyncMock(return_value=new_user)
        mock_link_repo.create = AsyncMock()

        auth_result = OAuthAuthResult(
            sub="oidc-789",
            email="newuser@example.com",
            display_name="New User",
            email_verified=True,
        )
        mock_provider = MagicMock()
        mock_provider.id = uuid.uuid4()
        community_id = uuid.uuid4()

        with patch(
            "app.services.oauth.user_provisioner.UserOAuthLinkRepository",
            return_value=mock_link_repo,
        ):
            with patch(
                "app.services.oauth.user_provisioner.UserRepository",
                return_value=mock_user_repo,
            ):
                provisioner = UserProvisioner(mock_session, community_id)
                result = await provisioner.provision_user(auth_result, mock_provider, "member")

        assert result is new_user
        mock_user_repo.create.assert_called_once()
        user_created = mock_user_repo.create.call_args[0][0]
        assert user_created.email == "newuser@example.com"
        assert user_created.community_id == community_id
        assert user_created.role == "member"
        mock_link_repo.create.assert_called_once()


def _run(auth_result, *, link=None, user=None):
    """@brief Run provision_user with mocked repos; return (coro, link_repo, user_repo)."""
    link_repo, user_repo = AsyncMock(), AsyncMock()
    link_repo.find_by_provider_and_sub = AsyncMock(return_value=link)
    user_repo.find_by_email = AsyncMock(return_value=user)
    provider = MagicMock()
    provider.id = uuid.uuid4()

    async def go():
        with (
            patch("app.services.oauth.user_provisioner.UserOAuthLinkRepository", return_value=link_repo),
            patch("app.services.oauth.user_provisioner.UserRepository", return_value=user_repo),
        ):
            return await UserProvisioner(AsyncMock(), uuid.uuid4()).provision_user(
                auth_result, provider, "member"
            )

    return go(), link_repo, user_repo


class TestEmailVerification:
    """@brief Unverified emails must never create or link accounts."""

    @pytest.mark.asyncio
    async def test_unverified_email_rejected_for_new_user(self):
        coro, link_repo, user_repo = _run(OAuthAuthResult(sub="s", email="a@x.com"))
        with pytest.raises(AuthenticationError, match="Email not verified"):
            await coro
        user_repo.create.assert_not_called()
        link_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_unverified_email_cannot_link_existing_user(self):
        """Account-takeover guard."""
        existing = MagicMock(spec=User)
        coro, link_repo, _ = _run(OAuthAuthResult(sub="s", email="a@x.com"), user=existing)
        with pytest.raises(AuthenticationError, match="Email not verified"):
            await coro
        link_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_email_rejected(self):
        coro, _, user_repo = _run(OAuthAuthResult(sub="s", email=None, email_verified=True))
        with pytest.raises(AuthenticationError, match="Email not verified"):
            await coro
        user_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_verified_email_lookup_is_case_insensitive(self):
        existing = MagicMock(spec=User)
        existing.id = uuid.uuid4()
        coro, link_repo, user_repo = _run(
            OAuthAuthResult(sub="s", email="Mixed@X.com", email_verified=True), user=existing
        )
        assert await coro is existing
        user_repo.find_by_email.assert_called_once_with("mixed@x.com")
        link_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_returning_user_needs_no_verified_flag(self):
        link = MagicMock()
        link.user_id = uuid.uuid4()
        link.email_from_provider = "u@x.com"
        link.avatar_url = None
        user = MagicMock(spec=User)
        user.role = "member"
        coro, link_repo, user_repo = _run(OAuthAuthResult(sub="s", email="u@x.com"), link=link)
        user_repo.get_by_id = AsyncMock(return_value=user)
        assert await coro is user
        link_repo.create.assert_not_called()


class TestEmailVerifiedExtraction:
    """@brief Claim extractors populate email_verified strictly."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [(True, True), ("true", True), (False, False), ("false", False), (None, False), ("1", False)],
    )
    def test_extract_and_map(self, raw, expected):
        from app.services.oauth.claim_mapper import map_claims
        from app.services.oauth.token_verifier import extract_claims

        claims = {"sub": "s", "email": "a@x.com"}
        if raw is not None:
            claims["email_verified"] = raw
        assert extract_claims(claims, MagicMock(spec=[])).email_verified is expected
        assert map_claims(claims, None).email_verified is expected
