"""
@file imap_client.py
@brief Blocking IMAP helpers (SSL only, 20 s timeout). Run them in a thread.
       Credentials are never logged.
"""

from __future__ import annotations

import imaplib
import re
import ssl

TIMEOUT = 20
"""@brief Socket timeout in seconds."""

MAX_PER_POLL = 50
"""@brief Messages handled per poll."""

MAX_BYTES = 1_000_000
"""@brief Larger messages are skipped (and deleted) without being downloaded."""


def connect(host: str, port: int, user: str, password: str) -> imaplib.IMAP4_SSL:
    """
    @brief Open an SSL connection, log in and select INBOX.
    @throws imaplib.IMAP4.error on refused login; OSError on network trouble.
    """
    conn = imaplib.IMAP4_SSL(host, port, ssl_context=ssl.create_default_context(), timeout=TIMEOUT)
    try:
        conn.login(user, password)
        conn.select("INBOX")
    except Exception:
        _close(conn)
        raise
    return conn


def _close(conn: imaplib.IMAP4_SSL) -> None:
    try:
        conn.logout()
    except (imaplib.IMAP4.error, OSError):
        pass


def check(host: str, port: int, user: str, password: str) -> None:
    """@brief Log in and select INBOX, then disconnect (used by the Test button)."""
    _close(connect(host, port, user, password))


def fetch_unseen(
    host: str, port: int, user: str, password: str
) -> tuple[imaplib.IMAP4_SSL, list[tuple[bytes, bytes]]]:
    """
    @brief Fetch up to ``MAX_PER_POLL`` unseen messages without marking them seen.
    @return (open connection, [(message number, raw bytes)]); close via ``finish``.
    """
    conn = connect(host, port, user, password)
    try:
        _typ, data = conn.search(None, "UNSEEN")
        nums = (data[0] or b"").split()[:MAX_PER_POLL]
        out: list[tuple[bytes, bytes]] = []
        for num in nums:
            if _size(conn, num) > MAX_BYTES:
                out.append((num, b""))  # parses as empty -> ignored, then deleted
                continue
            _typ, parts = conn.fetch(num.decode(), "(BODY.PEEK[])")
            for part in parts:
                if isinstance(part, tuple):
                    out.append((num, bytes(part[1])))
                    break
    except Exception:
        _close(conn)
        raise
    return conn, out


def _size(conn: imaplib.IMAP4_SSL, num: bytes) -> int:
    """@brief RFC822.SIZE of one message (0 when the server doesn't say)."""
    _typ, data = conn.fetch(num.decode(), "(RFC822.SIZE)")
    head = data[0] if data else b""
    raw = head[0] if isinstance(head, tuple) else head
    m = re.search(rb"RFC822\.SIZE (\d+)", raw or b"")
    return int(m.group(1)) if m else 0


def finish(conn: imaplib.IMAP4_SSL, nums: list[bytes]) -> None:
    """@brief Flag the given messages deleted, expunge, and disconnect."""
    try:
        for num in nums:
            conn.store(num.decode(), "+FLAGS", "\\Deleted")
        if nums:
            conn.expunge()
    finally:
        _close(conn)
