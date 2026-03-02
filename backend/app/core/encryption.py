"""
@file encryption.py
@brief Fernet-based secret encryption for OAuth client secrets.

Derives a Fernet key from a config secret and provides encrypt/decrypt
for storing OAuth client secrets at rest.
"""

import base64
import hashlib

from cryptography.fernet import Fernet


def derive_fernet_key(secret_key: str) -> bytes:
    """
    @brief Derive a Fernet key from a secret string.

    Uses SHA-256 hash of the secret, then base64url encoding to produce
    a valid 32-byte Fernet key.

    @param secret_key Application secret (e.g. from settings).
    @return 32-byte key suitable for Fernet.
    """
    digest = hashlib.sha256(secret_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_secret(plaintext: str, fernet_key: bytes) -> str:
    """
    @brief Encrypt a plaintext string with Fernet.

    @param plaintext The secret to encrypt.
    @param fernet_key Key from derive_fernet_key().
    @return Base64-encoded ciphertext string.
    """
    f = Fernet(fernet_key)
    return f.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str, fernet_key: bytes) -> str:
    """
    @brief Decrypt a Fernet ciphertext.

    @param ciphertext Base64-encoded ciphertext from encrypt_secret().
    @param fernet_key Key from derive_fernet_key().
    @return Decrypted plaintext string.
    @raises InvalidToken If key is wrong or ciphertext is tampered.
    """
    f = Fernet(fernet_key)
    return f.decrypt(ciphertext.encode()).decode()
