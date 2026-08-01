"""SMTP delivery for tutoring reports, with optional CC recipients."""

from __future__ import annotations

import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def split_addresses(raw: str) -> list[str]:
    """Split a comma/semicolon separated address list into clean addresses."""
    return [a.strip() for a in re.split(r"[,;]", raw or "") if a.strip()]


def invalid_addresses(raw: str) -> list[str]:
    return [a for a in split_addresses(raw) if not _EMAIL_RE.match(a)]


def send_email(subject: str, text_body: str, html_body: str, to: str,
               cc: str = "", *, sender: str, password: str,
               host: str = "smtp.gmail.com", port: int = 587) -> tuple[bool, str]:
    """Send one multipart/alternative message. Returns (ok, message)."""
    if not sender or not password:
        return False, "Email configuration missing. Please check .env file."

    to_list = split_addresses(to)
    cc_list = split_addresses(cc)
    if not to_list:
        return False, "No recipient address."

    bad = invalid_addresses(to) + invalid_addresses(cc)
    if bad:
        return False, "Invalid email address: " + ", ".join(bad)

    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = subject

    # RFC 2046: the last part of a multipart message is the preferred one,
    # so HTML goes after plain text.
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(sender, password)
        # Cc recipients must be in the envelope too, or they never receive it.
        server.sendmail(sender, to_list + cc_list, msg.as_string())
        server.quit()
        return True, "Email sent successfully!"
    except Exception as e:
        return False, f"Failed to send email: {e}"
