"""
@file webauthn_soft.py
@brief Software ES256 WebAuthn authenticator (attestation ``none``) for tests.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
from typing import Any

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

ORIGIN, RPID = "https://home.example:8443", "home.example"


def b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class Auth:
    """@brief Software ES256 authenticator (attestation ``none``)."""

    def __init__(self, rpid: str = RPID) -> None:
        self.k = ec.generate_private_key(ec.SECP256R1())
        self.cid, self.n, self.rpid = os.urandom(16), 0, rpid

    def cose(self) -> bytes:
        n = self.k.public_key().public_numbers()
        x, y = n.x.to_bytes(32, "big"), n.y.to_bytes(32, "big")
        return cbor2.dumps({1: 2, 3: -7, -1: 1, -2: x, -3: y})

    def cdj(self, typ: str, chal: str, origin: str) -> bytes:
        body = {"type": typ, "challenge": chal, "origin": origin, "crossOrigin": False}
        return json.dumps(body).encode()

    def create(self, opts: dict[str, Any], origin: str = ORIGIN, uv: bool = True) -> dict[str, Any]:
        flags = 0x01 | (0x04 if uv else 0) | 0x40
        ad = (
            hashlib.sha256(self.rpid.encode()).digest()
            + bytes([flags])
            + struct.pack(">I", 0)
            + b"\0" * 16
            + struct.pack(">H", len(self.cid))
            + self.cid
            + self.cose()
        )
        att = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": ad})
        cdj = self.cdj("webauthn.create", opts["challenge"], origin)
        return {
            "id": b64(self.cid),
            "rawId": b64(self.cid),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64(cdj),
                "attestationObject": b64(att),
                "transports": ["internal"],
            },
        }

    def get(
        self,
        opts: dict[str, Any],
        origin: str = ORIGIN,
        uv: bool = True,
        count: int | None = None,
        rpid: str | None = None,
    ) -> dict[str, Any]:
        self.n = self.n + 1 if count is None else count
        flags = 0x01 | (0x04 if uv else 0)
        rp = hashlib.sha256((rpid or self.rpid).encode()).digest()
        ad = rp + bytes([flags]) + struct.pack(">I", self.n)
        c = self.cdj("webauthn.get", opts["challenge"], origin)
        sig = self.k.sign(ad + hashlib.sha256(c).digest(), ec.ECDSA(hashes.SHA256()))
        return {
            "id": b64(self.cid),
            "rawId": b64(self.cid),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64(c),
                "authenticatorData": b64(ad),
                "signature": b64(sig),
                "userHandle": None,
            },
        }
