"""Put messages in the sender's Gmail drafts folder over IMAP.

SMTP can only hand a message to a mail server for delivery; it has no notion
of a draft. A draft has to be appended to the mailbox itself, which is what
IMAP is for. Gmail accepts the same app password already used for sending, so
this needs no extra credentials and no OAuth consent screen.
"""

from __future__ import annotations

import imaplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.mailer import split_addresses

GMAIL_IMAP_HOST = "imap.gmail.com"
GMAIL_DRAFTS = "[Gmail]/Drafts"


def build_draft(subject: str, text_body: str, html_body: str, to: str, cc: str,
                sender: str) -> MIMEMultipart:
    """The message as it will sit in the drafts folder, ready to edit and send.

    An empty To is allowed on purpose: a report whose student is not in the
    roster still deserves a prepared draft, with the address left to fill in.
    """
    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    to_list = split_addresses(to)
    if to_list:
        msg["To"] = ", ".join(to_list)
    cc_list = split_addresses(cc)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = subject
    # RFC 2046: the last part is the preferred one, so HTML goes after text.
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


def save_drafts(messages: list[MIMEMultipart], *, sender: str, password: str,
                host: str = GMAIL_IMAP_HOST,
                folder: str = GMAIL_DRAFTS) -> list[tuple[bool, str]]:
    """Append every message to the drafts folder over one connection.

    Returns a result per message, in order. A connection-level failure fails
    them all rather than pretending some were saved.
    """
    if not messages:
        return []
    if not sender or not password:
        return [(False, "Email configuration missing.")] * len(messages)

    try:
        box = imaplib.IMAP4_SSL(host)
        box.login(sender, password)
    except Exception as e:
        return [(False, f"Could not reach the drafts folder: {e}")] * len(messages)

    results: list[tuple[bool, str]] = []
    try:
        for msg in messages:
            try:
                typ, _ = box.append(
                    folder, r"\Draft",
                    imaplib.Time2Internaldate(time.time()), msg.as_bytes())
                results.append(
                    (typ == "OK", "Draft saved" if typ == "OK"
                     else f"Gmail refused the draft ({typ})"))
            except Exception as e:
                results.append((False, f"Could not save the draft: {e}"))
    finally:
        try:
            box.logout()
        except Exception:
            pass
    return results
