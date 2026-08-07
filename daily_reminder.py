"""Email the director the reports still waiting for review.

Runs from GitHub Actions on a schedule; nothing about it is Streamlit-specific.

Sends nothing when the queue is empty. A mail that arrives every morning
whether or not it means anything is a mail you stop reading, and the point of
this is to be noticed on the mornings something is actually waiting.

    python daily_reminder.py             # only acts at REMINDER_HOUR local time
    python daily_reminder.py --force     # act now, whatever the clock says
    python daily_reminder.py --dry-run   # print the mail instead of sending it
"""

from __future__ import annotations

import sys
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import config
from src import report as report_lib
from src import store
from src.mailer import send_email

REMINDER_HOUR = 11          # local hour, see the workflow for why this is checked here


def _waited_days(created_at: str, now: datetime) -> int:
    """Whole days since submission, 0 if the timestamp is unreadable."""
    try:
        return max(0, (now - datetime.fromisoformat(created_at)).days)
    except (TypeError, ValueError):
        return 0


def build_reminder(pending: list[dict], now: datetime) -> tuple[str, str, str]:
    """(subject, text body, html body) for a non-empty list of waiting reports."""
    n = len(pending)
    subject = f"[Tutoring] {n} report{'s' if n != 1 else ''} waiting for review"

    rows = []
    for e in pending:
        r = e.get("report", {})
        d = report_lib.to_date(r.get("class_date"))
        rows.append({
            "student": r.get("student_name") or "(no name)",
            "date": d.strftime("%m/%d/%Y") if d else "?",
            "teacher": r.get("teacher_name") or "",
            "days": _waited_days(e.get("created_at", ""), now),
        })

    plural, verb = ("s", "need") if n != 1 else ("", "needs")
    lines = [f"{n} tutoring report{plural} still {verb} to be reviewed and "
             "sent to parents.", ""]
    for r in rows:
        waited = "submitted today" if r["days"] == 0 else f"waiting {r['days']} day(s)"
        lines.append(f"  - {r['student']} — {r['date']} — {r['teacher']} ({waited})")
    lines += ["", f"Review and send them here: {config.REVIEW_APP_URL}"]
    text = "\n".join(lines)

    cells = "".join(
        f"<tr>"
        f"<td style='padding:6px 12px 6px 0'>{escape(r['student'])}</td>"
        f"<td style='padding:6px 12px 6px 0'>{r['date']}</td>"
        f"<td style='padding:6px 12px 6px 0'>{escape(r['teacher'])}</td>"
        f"<td style='padding:6px 0;color:{'#c0392b' if r['days'] >= 2 else '#666'}'>"
        f"{'today' if r['days'] == 0 else str(r['days']) + 'd'}</td>"
        f"</tr>"
        for r in rows)
    html = (
        "<div style=\"font-family:-apple-system,Segoe UI,Arial,sans-serif;"
        "font-size:14px;color:#222\">"
        f"<p><b>{n}</b> tutoring report{plural} still {verb} to be reviewed "
        "and sent to parents.</p>"
        "<table style='border-collapse:collapse'>"
        "<tr style='text-align:left;color:#666;font-size:12px'>"
        "<th style='padding-right:12px'>Student</th>"
        "<th style='padding-right:12px'>Class date</th>"
        "<th style='padding-right:12px'>Teacher</th>"
        "<th>Waiting</th></tr>"
        f"{cells}</table>"
        f"<p><a href=\"{escape(config.REVIEW_APP_URL)}\">Open the review app</a></p>"
        "</div>")
    return subject, text, html


def main(argv: list[str]) -> int:
    force = "--force" in argv
    dry_run = "--dry-run" in argv
    now = datetime.now(ZoneInfo(config.LOCAL_TZ))

    # The scheduler fires in UTC and the offset here moves with daylight saving,
    # so the workflow fires on both candidate hours and this decides which one
    # is really 11am today.
    if not force and now.hour != REMINDER_HOUR:
        print(f"Local time is {now:%H:%M} ({config.LOCAL_TZ}); "
              f"the reminder hour is {REMINDER_HOUR}:00. Nothing to do.")
        return 0

    try:
        pending = [e for e in store.load_all() if e.get("status") != store.SENT]
    except Exception as e:
        print(f"Could not read the reports sheet: {e}", file=sys.stderr)
        return 1

    if not pending:
        print("Nothing is waiting for review. No mail sent.")
        return 0

    subject, text, html = build_reminder(pending, now)

    if dry_run:
        print(f"To: {config.RECEIVER_EMAIL}\nSubject: {subject}\n\n{text}")
        return 0

    ok, msg = send_email(
        subject, text, html, config.RECEIVER_EMAIL,
        sender=config.SENDER_EMAIL, password=config.SENDER_PASSWORD,
        host=config.SMTP_HOST, port=config.SMTP_PORT)
    print(msg)
    if ok:
        print(f"Reminded about {len(pending)} report(s).")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
