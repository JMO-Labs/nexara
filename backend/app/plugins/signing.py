"""
@file signing.py
@brief HMAC-SHA256 webhook signatures: ``sha256=HMAC(secret, "<timestamp>.<body>")``.
"""

from __future__ import annotations

import hashlib
import hmac


def sign(secret: str, timestamp: int, body: bytes) -> str:
    """
    @brief Sign a webhook body.
    @param secret Plain webhook secret.
    @param timestamp Unix seconds sent in ``X-Nexara-Timestamp``.
    @param body Exact request body bytes.
    @return ``"sha256=<hex>"``.
    """
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def verify(
    secret: str, timestamp: int, body: bytes, signature: str, now: int, max_age: int = 300
) -> bool:
    """
    @brief Constant-time check of a signature and its freshness.
    @param now Current unix seconds.
    @param max_age Reject timestamps older (or further in the future) than this.
    @return True when the signature matches and the timestamp is fresh.
    """
    if abs(now - timestamp) > max_age:
        return False
    return hmac.compare_digest(sign(secret, timestamp, body), signature)
