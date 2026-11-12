"""@file Unit tests for HookRegistry."""

import asyncio
import logging
import uuid
from unittest.mock import AsyncMock

import pytest

from app.plugins import hooks as hooks_mod
from app.plugins.hooks import HOOK_EVENTS, HookRegistry
from app.plugins.manifest import PluginManifest

COMMUNITY = uuid.uuid4()


def _manifest(pid="p1", hooks=None, perms=None) -> PluginManifest:
    ev = ["before_post_created", "after_post_created"] if hooks is None else hooks
    return PluginManifest.model_validate(
        {
            "id": pid, "name": "P", "version": "1.0.0", "author": "a",
            "description": "d", "min_core_version": "0.1.0",
            "permissions": ["hooks_before_post_created", "hooks_after_post_created"]
            if perms is None else perms,
            "hooks": {e: "d" for e in ev},
        }
    )  # fmt: skip


@pytest.fixture(autouse=True)
def _reset():
    HookRegistry.reset()
    yield
    HookRegistry.reset()


async def _emit(event="after_post_created", **kw):
    return await HookRegistry.emit(event, community_id=COMMUNITY, session=AsyncMock(), **kw)


class TestRegister:
    async def test_registered_hook_fires(self):
        h = AsyncMock(return_value=7)
        HookRegistry.register("after_post_created", "p1", h, _manifest())
        assert await _emit(post_id=1) == [7]

    async def test_handler_receives_ctx_and_kwargs(self):
        h = AsyncMock()
        HookRegistry.register("after_post_created", "p1", h, _manifest())
        await _emit(post_id=1, content="x")
        ctx = h.call_args.args[0]
        assert ctx.plugin_id == "p1" and ctx.community_id == COMMUNITY
        assert h.call_args.kwargs == {"post_id": 1, "content": "x"}

    def test_unknown_event_rejected(self):
        with pytest.raises(ValueError):
            HookRegistry.register("nope", "p1", AsyncMock(), _manifest(hooks=["nope"]))

    def test_event_not_in_manifest_hooks_rejected(self):
        with pytest.raises(ValueError):
            HookRegistry.register("on_user_joined", "p1", AsyncMock(), _manifest())

    async def test_skipped_without_permission(self):
        h = AsyncMock()
        m = _manifest(perms=[])
        HookRegistry.register("after_post_created", "p1", h, m)
        assert await _emit() == []
        h.assert_not_called()

    def test_all_events_defined(self):
        assert set(HOOK_EVENTS) == {
            "before_post_created", "after_post_created", "before_chat_sent",
            "after_chat_sent", "on_user_joined", "on_community_created",
        }  # fmt: skip


class TestEmit:
    async def test_no_handlers(self):
        assert await _emit() == []

    async def test_error_logged_not_raised(self, caplog):
        bad = AsyncMock(side_effect=RuntimeError("boom"))
        good = AsyncMock(return_value=1)
        HookRegistry.register("after_post_created", "bad", bad, _manifest("bad"))
        HookRegistry.register("after_post_created", "good", good, _manifest("good"))
        with caplog.at_level(logging.ERROR):
            assert await _emit() == [1]
        assert any(r.levelno == logging.ERROR for r in caplog.records)

    async def test_timeout_cancelled(self, monkeypatch):
        monkeypatch.setattr(hooks_mod, "HANDLER_TIMEOUT", 0.01)

        async def slow(ctx, **kw):
            await asyncio.sleep(5)

        HookRegistry.register("after_post_created", "p1", slow, _manifest())
        assert await _emit() == []

    async def test_unknown_event_emit_is_noop(self):
        assert await _emit("nope") == []


class TestPostServiceIntegration:
    async def test_create_post_emits_hooks(self):
        from unittest.mock import MagicMock

        from app.models.user import User
        from app.services.post_service import PostService

        calls = []

        async def handler(ctx, **kw):
            calls.append(kw)

        for ev in ("before_post_created", "after_post_created"):
            HookRegistry.register(ev, "p1", handler, _manifest())
        repo = AsyncMock()
        repo.create_post.return_value = MagicMock(id=uuid.uuid4(), subgroup_id=None)
        repo.get_post_detail.return_value = {"id": "x"}
        svc = PostService(repo, AsyncMock(), AsyncMock(), AsyncMock(), COMMUNITY)
        svc._notify_mentions = AsyncMock()
        user = MagicMock(spec=User, id=uuid.uuid4())
        await svc.create_post(user, "hello")
        assert len(calls) == 2 and calls[0]["content"] == "hello"
        assert "post_id" in calls[1]
