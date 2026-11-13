"""@file Unit tests for plugin permission enforcement and API keys."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthenticationError
from app.models.plugin import PluginApiKey
from app.plugins.api_keys import (
    generate_api_key,
    parse_api_key,
    resolve_plugin_from_key,
    verify_api_key,
)
from app.plugins.manifest import PluginManifest, PluginPermission
from app.plugins.permissions import check_permission, enforce_permission
from app.repositories.plugin_key_repo import PluginApiKeyRepository


def _manifest(perms: list[str]) -> PluginManifest:
    return PluginManifest.model_validate(
        {
            "id": "hello",
            "name": "Hello",
            "version": "1.0.0",
            "author": "a",
            "description": "d",
            "min_core_version": "0.1.0",
            "permissions": perms,
        }
    )


class TestEnforcePermission:
    def test_granted_passes(self) -> None:
        enforce_permission(_manifest(["db_read"]), "db_read")

    def test_enum_accepted(self) -> None:
        enforce_permission(_manifest(["db_read"]), PluginPermission.DB_READ)

    def test_missing_raises(self) -> None:
        with pytest.raises(PermissionError, match="db_write"):
            enforce_permission(_manifest(["db_read"]), "db_write")

    def test_unknown_permission_raises(self) -> None:
        with pytest.raises(PermissionError):
            enforce_permission(_manifest(["db_read"]), "nope")

    def test_check_permission_uses_context_manifest(self) -> None:
        ctx = MagicMock()
        ctx.manifest = _manifest(["external_http"])
        ctx.plugin_id = "hello"
        check_permission(ctx, "external_http")
        with pytest.raises(PermissionError):
            check_permission(ctx, "db_write")


class TestApiKeyFormat:
    def test_format_and_hash(self) -> None:
        plain, hashed = generate_api_key("hello")
        assert plain.startswith("nxr_plugin_hello_")
        assert len(plain.rsplit("_", 1)[1]) == 32
        assert hashed != plain and hashed.startswith("$2")
        assert verify_api_key(plain, hashed)
        assert not verify_api_key(plain + "0", hashed)

    def test_keys_unique(self) -> None:
        assert generate_api_key("a")[0] != generate_api_key("a")[0]

    def test_parse_plugin_id_with_underscore(self) -> None:
        plain, _h = generate_api_key("my_plugin")
        assert parse_api_key(plain) == "my_plugin"

    @pytest.mark.parametrize("bad", ["", "abc", "nxr_plugin_", "nxr_plugin_x_zz", "jwt.a.b"])
    def test_parse_rejects_malformed(self, bad: str) -> None:
        assert parse_api_key(bad) is None


COMMUNITY = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _session_with(rows: list[PluginApiKey]) -> AsyncMock:
    """Session whose repo query yields rows (repo patched in resolve())."""
    session = AsyncMock()
    session.rows = rows
    return session


async def resolve(session: AsyncMock, key: str) -> str:
    with patch("app.plugins.api_keys.PluginApiKeyRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.active_keys_for_plugin = AsyncMock(return_value=session.rows)
        try:
            return await resolve_plugin_from_key(session, key, COMMUNITY)
        finally:
            session.repo = repo


def _row(plain_hash: str, revoked: bool = False) -> MagicMock:
    row = MagicMock(spec=PluginApiKey)
    row.id = uuid.uuid4()
    row.plugin_id = "hello"
    row.key_hash = plain_hash
    row.revoked_at = datetime.now(UTC) if revoked else None
    row.last_used_at = None
    return row


class TestResolve:
    async def test_valid_key_returns_plugin_and_touches(self) -> None:
        plain, hashed = generate_api_key("hello")
        row = _row(hashed)
        assert await resolve(_session_with([row]), plain) == "hello"
        assert row.last_used_at is not None

    async def test_no_active_rows_rejected(self) -> None:
        plain, _h = generate_api_key("hello")
        with pytest.raises(AuthenticationError):
            await resolve(_session_with([]), plain)

    async def test_wrong_hash_rejected(self) -> None:
        plain, _h = generate_api_key("hello")
        _p, other = generate_api_key("hello")
        with pytest.raises(AuthenticationError):
            await resolve(_session_with([_row(other)]), plain)

    async def test_revoked_rejected_even_if_hash_matches(self) -> None:
        plain, hashed = generate_api_key("hello")
        with pytest.raises(AuthenticationError):
            await resolve(_session_with([_row(hashed, revoked=True)]), plain)

    async def test_malformed_rejected(self) -> None:
        with pytest.raises(AuthenticationError):
            await resolve(_session_with([]), "garbage")

    async def test_lookup_scoped_to_community(self) -> None:
        plain, hashed = generate_api_key("hello")
        session = _session_with([_row(hashed)])
        await resolve(session, plain)
        session.repo.active_keys_for_plugin.assert_awaited_once_with("hello", COMMUNITY)

    async def test_disabled_or_deleted_plugin_yields_no_keys_rejected(self) -> None:
        # Repo returns nothing for disabled / soft-deleted plugins.
        plain, _h = generate_api_key("hello")
        with pytest.raises(AuthenticationError):
            await resolve(_session_with([]), plain)


class TestActiveKeysQuery:
    async def test_filters_plugin_state_and_community(self) -> None:
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute.return_value = result
        await PluginApiKeyRepository(session).active_keys_for_plugin("hello", COMMUNITY)
        sql = str(session.execute.call_args.args[0].compile(compile_kwargs={"literal_binds": True}))
        assert "plugins.deleted_at IS NULL" in sql
        assert "plugins.is_enabled" in sql
        assert "plugin_api_keys.revoked_at IS NULL" in sql
        assert str(COMMUNITY) in sql or COMMUNITY.hex in sql


class TestVerifyMalformedHash:
    def test_invalid_hash_returns_false(self) -> None:
        assert verify_api_key("nxr_plugin_hello_" + "a" * 32, "not-a-bcrypt-hash") is False


def test_check_permission_reads_context_manifest():
    """check_permission enforces against ctx.manifest."""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from app.plugins.permissions import check_permission

    manifest = MagicMock()
    manifest.id = "p"
    manifest.permissions = set()
    with pytest.raises(PermissionError):
        check_permission(SimpleNamespace(manifest=manifest), "db_read")
