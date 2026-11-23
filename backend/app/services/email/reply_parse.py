"""
@file reply_parse.py
@brief Parse inbound reply emails: token from the address, the reply text with
       quotes and signature removed, auto-reply and sender checks. Stdlib only.
"""

from __future__ import annotations

import re
from email.message import Message
from email.utils import getaddresses, parseaddr
from html.parser import HTMLParser

MAX_BODY = 5000
"""@brief Longest reply (after cleaning) that is accepted."""

_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{24}$")  # token_urlsafe(18) is 24 chars
_WROTE_RE = re.compile(r"^On .*wrote:\s*$", re.DOTALL)
_ORIGINAL_RE = re.compile(r"^-{3,}\s*Original Message\s*-{3,}\s*$", re.IGNORECASE)
_BULK = {"bulk", "list", "auto_reply", "junk"}
_BLOCK_TAGS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}
_SKIP_TAGS = {"script", "style", "head", "title"}


def extract_token(addresses: list[str], base_local: str) -> str | None:
    """
    @brief Find ``<base_local>+<token>@...`` among recipient headers.
    @param addresses Raw header values (To, Cc, Delivered-To, ...).
    @param base_local Local part of the configured reply address (no plus tag).
    @return The raw token, or None when no address carries a well-formed one.
    """
    prefix = base_local.lower() + "+"
    for _name, addr in getaddresses(addresses):
        local = addr.rpartition("@")[0]
        if local.lower().startswith(prefix):
            token = local[len(prefix) :]
            if _TOKEN_RE.match(token):
                return token
    return None


def is_auto_reply(msg: Message) -> bool:
    """@return True for out-of-office / bulk / list mail that must never be posted."""
    auto = msg.get("Auto-Submitted")
    if auto is not None and str(auto).strip().lower() != "no":
        return True
    return str(msg.get("Precedence", "")).strip().lower() in _BULK


def sender_address(msg: Message) -> str | None:
    """@return The lower-cased From address; None if missing or the header repeats."""
    froms = msg.get_all("From") or []
    if len(froms) != 1:
        return None
    addr = parseaddr(str(froms[0]))[1].strip().lower()
    return addr or None


class _Text(HTMLParser):
    """@brief HTML to text; drops script/style and quoted blocks (blockquote, gmail_quote)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self._stack: list[tuple[str, bool]] = []  # (tag, opened a skipped region)
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        quote = tag == "blockquote" or (
            tag == "div" and "gmail_quote" in (dict(attrs).get("class") or "")
        )
        skip = quote or tag in _SKIP_TAGS
        if tag not in ("br", "img", "hr", "meta", "link", "input"):
            self._stack.append((tag, skip))
            self._skip += skip
        if tag in _BLOCK_TAGS and not self._skip:
            self.out.append("\n")

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                for _t, skip in self._stack[i:]:
                    self._skip -= skip
                del self._stack[i:]
                break
        if tag in _BLOCK_TAGS and not self._skip:
            self.out.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.out.append(data)


def _decode(part: Message) -> str:
    raw = part.get_payload(decode=True)
    if not isinstance(raw, bytes):
        return ""
    try:
        return raw.decode(part.get_content_charset() or "utf-8", errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def _raw_text(msg: Message) -> str:
    """@brief text/plain if present, else tag-stripped HTML."""
    plain = html = None
    for part in msg.walk():
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue
        kind = part.get_content_type()
        if kind == "text/plain" and plain is None:
            plain = _decode(part)
        elif kind == "text/html" and html is None:
            html = _decode(part)
    if plain is not None:
        return plain
    if html is None:
        return ""
    parser = _Text()
    parser.feed(html)
    parser.close()
    return "".join(parser.out)


def _is_cut(lines: list[str], i: int) -> bool:
    line = lines[i].strip()
    if line.startswith(">") or line.startswith("From: ") or _ORIGINAL_RE.match(line):
        return True
    joined = line if i + 1 >= len(lines) else f"{line} {lines[i + 1].strip()}"
    return bool(line.startswith("On ") and (_WROTE_RE.match(line) or _WROTE_RE.match(joined)))


def clean_body(msg: Message) -> str | None:
    """
    @brief The new text of a reply, without quoted history or signature.
    @param msg Parsed inbound message.
    @return Cleaned text; None when empty or longer than ``MAX_BODY``.
    """
    lines = _raw_text(msg).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    kept: list[str] = []
    for i, line in enumerate(lines):
        if _is_cut(lines, i) or line.rstrip() in ("--", "-- "):
            break
        kept.append(line.rstrip())
    while kept and (not kept[-1].strip() or set(kept[-1].strip()) == {"_"}):
        kept.pop()  # trailing blanks and Outlook's "____" divider
    text = "\n".join(kept).strip()
    return text if text and len(text) <= MAX_BODY else None


_AUTH_PASS = re.compile(
    r"\b(?:dkim=pass[^;]*header\.(?:d|i)=@?(?P<d>[\w.-]+)"
    r"|dmarc=pass[^;]*header\.from=(?P<f>[\w.-]+))",
    re.I,
)


def authenticated(msg: Message, sender: str | None) -> bool:
    """
    @brief The receiving server vouched for the sender's domain: the topmost
           Authentication-Results header has dkim=pass or dmarc=pass aligned
           with the From domain. The token alone is a bearer secret; this
           stops a leaked reply address being used with a forged From.
    """
    if not sender or "@" not in sender:
        return False
    domain = sender.rsplit("@", 1)[1].lower()
    results = msg.get_all("Authentication-Results") or []
    if not results:
        return False
    for m in _AUTH_PASS.finditer(str(results[0])):
        got = (m.group("d") or m.group("f") or "").lower()
        if got == domain or domain.endswith("." + got):
            return True
    return False
