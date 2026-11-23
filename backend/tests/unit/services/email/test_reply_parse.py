"""
@file test_reply_parse.py
@brief reply_parse: token extraction, quote/signature stripping on Gmail, Outlook
       and Apple Mail style replies, auto-reply and sender checks.
"""

from __future__ import annotations

from email import message_from_bytes
from email.message import EmailMessage

from app.services.email.reply_parse import (
    clean_body,
    extract_token,
    is_auto_reply,
    sender_address,
)

TOKEN = "A" * 24


def _msg(plain: str | None = None, html: str | None = None, **headers: str) -> EmailMessage:
    m = EmailMessage()
    m["From"] = headers.pop("From", "Ruth <ruth@example.com>")
    m["To"] = f"reply+{TOKEN}@mail.example.com"
    for k, v in headers.items():
        m[k.replace("_", "-")] = v
    if plain is not None:
        m.set_content(plain)
        if html is not None:
            m.add_alternative(html, subtype="html")
    elif html is not None:
        m.set_content(html, subtype="html")
    return m


def test_extract_token_variants():
    assert extract_token([f"Nexara <reply+{TOKEN}@x.org>"], "reply") == TOKEN
    assert extract_token(["a@b.com", f"REPLY+{TOKEN}@x.org"], "reply") == TOKEN
    assert extract_token(["reply@x.org"], "reply") is None
    assert extract_token(["reply+short@x.org"], "reply") is None
    assert extract_token([f"other+{TOKEN}@x.org"], "reply") is None
    assert extract_token([], "reply") is None


def test_gmail_plain_wrapped_attribution():
    body = (
        "Sounds great, see you there!\n\n"
        "On Mon, Nov 3, 2025 at 4:12 PM Nexara Family <reply+x@mail.example.com>\n"
        "wrote:\n\n> Dad commented on your post\n> hello\n"
    )
    assert clean_body(_msg(body)) == "Sounds great, see you there!"


def test_gmail_html_only_drops_gmail_quote():
    html = (
        '<div dir="ltr">Count me in<br>Thanks</div><br>'
        '<div class="gmail_quote"><div>On Mon, Nov 3 Nexara wrote:</div>'
        "<blockquote><p>Old text</p></blockquote></div>"
    )
    assert clean_body(_msg(html=html)) == "Count me in\nThanks"


def test_outlook_original_message_and_from_header():
    body = "Yes please.\r\n\r\n-----Original Message-----\r\nFrom: Nexara\r\nSent: Monday\r\nhi\r\n"
    assert clean_body(_msg(body)) == "Yes please."
    body2 = (
        "Yes please.\n\n________________________________\nFrom: Nexara <x@y.com>\nSent: Monday\n"
    )
    assert clean_body(_msg(body2)) == "Yes please."


def test_outlook_html_with_blockquote():
    html = "<html><head><style>p{}</style></head><body><p>Love it</p><hr>"
    html += "<blockquote>quoted</blockquote></body></html>"
    assert clean_body(_msg(html=html)) == "Love it"


def test_apple_mail_attribution_and_signature():
    body = (
        "Congrats!!\n\n-- \nRuth\nSent from my iPhone\n\n"
        "> On Nov 3, 2025, at 4:12 PM, Nexara <x@y.com> wrote:\n> hi\n"
    )
    assert clean_body(_msg(body)) == "Congrats!!"
    body2 = "Nice one\n\nOn Nov 3, 2025, at 4:12 PM, Nexara <x@y.com> wrote:\n\n> hi"
    assert clean_body(_msg(body2)) == "Nice one"


def test_prefers_plain_over_html():
    assert clean_body(_msg("plain text", "<p>html text</p>")) == "plain text"


def test_empty_only_quote_and_too_long_are_none():
    assert clean_body(_msg("\n\n> quoted only\n")) is None
    assert clean_body(_msg("   \n")) is None
    assert clean_body(_msg("x" * 5001)) is None
    assert clean_body(_msg("x" * 5000)) == "x" * 5000


def test_attachment_text_ignored():
    m = _msg("real reply")
    m.add_attachment(b"secret", maintype="text", subtype="plain", filename="a.txt")
    assert clean_body(m) == "real reply"


def test_auto_reply_detection():
    assert is_auto_reply(_msg("hi", Auto_Submitted="auto-replied"))
    assert not is_auto_reply(_msg("hi", Auto_Submitted="no"))
    for p in ("bulk", "list", "auto_reply", "junk"):
        assert is_auto_reply(_msg("hi", Precedence=p))
    assert not is_auto_reply(_msg("hi"))


def test_sender_address():
    assert sender_address(_msg("hi", From="Ruth <Ruth@Example.COM>")) == "ruth@example.com"
    raw = b"From: a@example.com\nFrom: evil@example.com\n\nhi"
    assert sender_address(message_from_bytes(raw)) is None
