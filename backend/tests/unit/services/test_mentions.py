"""@file Unit tests for the pure mentions.extract utility."""

from app.services import mentions


class TestExtract:
    """@brief Tests for mentions.extract()."""

    def test_extracts_usernames(self):
        assert mentions.extract("Hey @alice and @bob_123, hi") == ["alice", "bob_123"]

    def test_ignores_inline_code(self):
        assert mentions.extract("Use `@handle` but @alice is real") == ["alice"]

    def test_ignores_multiline_fence(self):
        assert mentions.extract("```\n@x\n```\n@y") == ["y"]

    def test_deduplicates_preserving_order(self):
        assert mentions.extract("@b @a @b") == ["b", "a"]

    def test_empty(self):
        assert mentions.extract("") == []

    def test_hyphen_allowed(self):
        assert mentions.extract("@a-b") == ["a-b"]
