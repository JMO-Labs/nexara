"""@file secrets.py
@brief Fernet helpers for encrypting Apprise URLs at rest.

The key comes from the ``APPRISE_ENCRYPTION_KEY`` env var (a urlsafe base64
32-byte Fernet key). Plaintext URLs embed credentials; never log them.
"""

import os

from cryptography.fernet import Fernet

KEY_ENV = "APPRISE_ENCRYPTION_KEY"


def _fernet() -> Fernet:
    key = os.environ.get(KEY_ENV, "")
    if not key:
        raise RuntimeError(f"{KEY_ENV} is not set")
    return Fernet(key.encode())


def encrypt_url(url: str) -> str:
    """@param url Plaintext Apprise URL. @return Fernet token (str)."""
    return _fernet().encrypt(url.encode()).decode()


def decrypt_url(token: str) -> str:
    """@param token Fernet token. @return Plaintext Apprise URL."""
    return _fernet().decrypt(token.encode()).decode()
