"""
@file encryption.py
@brief Fernet symmetric encryption for sensitive values like OAuth client secrets.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet


def derive_fernet_key(secret_key: str) -> bytes:
    """@brief Derive a Fernet-compatible key from an application secret."""
    digest = hashlib.sha256(secret_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_secret(plaintext: str, key: bytes) -> str:
    """@brief Encrypt a string using Fernet and return the ciphertext."""
    f = Fernet(key)
    return f.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str, key: bytes) -> str:
    """@brief Decrypt a Fernet-encrypted string."""
    f = Fernet(key)
    return f.decrypt(ciphertext.encode()).decode()
