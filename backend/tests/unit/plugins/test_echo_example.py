"""
@file test_echo_example.py
@brief The echo example's verify() must agree with core signing.
"""

import importlib.util
from pathlib import Path

from app.plugins.signing import sign

_p = Path(__file__).resolve().parents[4] / "scripts" / "plugin-echo" / "echo.py"
_spec = importlib.util.spec_from_file_location("plugin_echo", _p)
assert _spec and _spec.loader
echo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(echo)

BODY = b'{"event":"mention"}'


def test_accepts_core_signature() -> None:
    assert echo.verify("s", "1000", BODY, sign("s", 1000, BODY), now=1100)


def test_rejects_tamper_wrong_secret_and_stale() -> None:
    sig = sign("s", 1000, BODY)
    assert not echo.verify("s", "1000", BODY + b" ", sig, now=1000)
    assert not echo.verify("x", "1000", BODY, sig, now=1000)
    assert not echo.verify("s", "1000", BODY, sig, now=1301)
    assert not echo.verify("s", "bad", BODY, sig, now=1000)
