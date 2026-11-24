"""
@file test_signing.py
@brief Webhook HMAC signing and freshness checks.
"""

import hashlib
import hmac

from app.plugins.signing import sign, verify


def test_sign_known_vector():
    expect = hmac.new(b"s", b"1700000000.{}", hashlib.sha256).hexdigest()
    assert sign("s", 1700000000, b"{}") == f"sha256={expect}"


def test_verify_roundtrip():
    sig = sign("s", 1700000000, b"{}")
    assert verify("s", 1700000000, b"{}", sig, now=1700000100)


def test_verify_rejects_old_timestamp():
    sig = sign("s", 1700000000, b"{}")
    assert not verify("s", 1700000000, b"{}", sig, now=1700000301)


def test_verify_rejects_tampered_body():
    sig = sign("s", 1700000000, b"{}")
    assert not verify("s", 1700000000, b'{"a":1}', sig, now=1700000001)
