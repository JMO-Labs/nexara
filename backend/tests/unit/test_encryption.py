"""
@file test_encryption.py
@brief Unit tests for Fernet secret encryption utility.
"""

import pytest

from app.core.encryption import decrypt_secret, derive_fernet_key, encrypt_secret


class TestEncryption:
    """@brief Tests for derive_fernet_key, encrypt_secret, decrypt_secret."""

    def test_derive_key_deterministic(self):
        """derive_fernet_key should return the same key for same input."""
        key1 = derive_fernet_key("my-secret-key")
        key2 = derive_fernet_key("my-secret-key")
        assert key1 == key2

    def test_derive_key_different_inputs(self):
        """derive_fernet_key should return different keys for different inputs."""
        key1 = derive_fernet_key("key-a")
        key2 = derive_fernet_key("key-b")
        assert key1 != key2

    def test_round_trip(self):
        """encrypt_secret and decrypt_secret should round-trip correctly."""
        key = derive_fernet_key("test-secret-key-at-least-32-chars-long")
        plaintext = "my-client-secret"
        encrypted = encrypt_secret(plaintext, key)
        assert encrypted != plaintext
        assert decrypt_secret(encrypted, key) == plaintext

    def test_wrong_key_fails(self):
        """decrypt_secret with wrong key should raise an exception."""
        key1 = derive_fernet_key("key-one-long-enough")
        key2 = derive_fernet_key("key-two-long-enough")
        encrypted = encrypt_secret("secret", key1)
        with pytest.raises(Exception):
            decrypt_secret(encrypted, key2)

    def test_empty_string(self):
        """Empty string should encrypt and decrypt correctly."""
        key = derive_fernet_key("test-key-long-enough")
        encrypted = encrypt_secret("", key)
        assert decrypt_secret(encrypted, key) == ""
