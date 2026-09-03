"""Nudge a teacher whose tutoring session ended an hour ago with no report.

Runs every 15 minutes from GitHub Actions. For each "[TUT]" session on the
director's calendar that ended at least REMINDER_DELAY_MINUTES ago, it looks
for a submitted report from the same teacher, for the same student, on the
same day. Finding none, it emails the teacher once and notes that on the
Reminders tab so the next run leaves that session alone.

    python remind_missing_reports.py             # do it
    python remind_missing_reports.py --dry-run   # say what it would do
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo

import config
from src import reminder_log, store
from src.auth import default_credentials
from src.calendar_events import Session, fetch_sessions
from src.mailer import send_email
from src.students import _name_words
from src.teachers import find_teacher, parse_teachers


# --- Deciding whether a session already has its report (pure) ---------------

def report_matches_session(report: dict, session: Session) -> bool:
    """Same day, same teacher, same student, allowing for how teachers type.

    The calendar says "Joseph teacher" and "Kyuheon (Andrew) Ahn"; the form
    gets "Joseph O'Hailey" and "Andrew". So the teacher matches on the first
    word, and the student matches when one name's words are a subset of the
    other's. Known gap: two siblings with the same teacher on the same day
    cannot be told apart by a report that gives only their surname.
    """
    if str(report.get("class_date", ""))[:10] != session.start.date().isoformat():
        return False

    cal_teacher = session.teacher.split()
    typed_teacher = _name_words(report.get("teacher_name", ""))
    if not cal_teacher or cal_teacher[0].lower() not in typed_teacher:
        return False

    typed = _name_words(report.get("student_name", ""))
    scheduled = _name_words(session.student)
    if not typed or not scheduled:
        return False
    return typed <= scheduled or scheduled <= typed


def sessions_due(sessions: list[Session], now: datetime) -> list[Session]:
    """Not canceled, and ended between the lookback limit and the delay ago."""
    newest = now - timedelta(minutes=config.REMINDER_DELAY_MINUTES)
    oldest = now - timedelta(hours=config.REMINDER_LOOKBACK_HOURS)
    return [s for s in sessions if not s.canceled and oldest <= s.end <= newest]


# --- The email --------------------------------------------------------------

def _clock(t: datetime) -> str:
    return t.strftime("%I:%M %p").lstrip("0")


def build_reminder(session: Session, teacher_first_name: str) -> tuple[str, str, str]:
    tz = ZoneInfo(config.LOCAL_TZ)
    start, end = session.start.astimezone(tz), session.end.astimezone(tz)
    day = f"{start:%b} {start.day}"
    span = f"{_clock(start)}–{_clock(end)}"
    subject_part = f", {session.subject}" if session.subject else ""

    subject = f"Tutoring report needed: {session.student} — {day}, {span}"
    text = (
        f"Hi {teacher_first_name},\n\n"
        f"The tutoring report for {session.student} ({day}, {span}{subject_part}) "
        "hasn't been submitted yet.\n\n"
        f"Please submit it here: {config.TEACHER_FORM_URL}\n\n"
        "If you have already submitted it, please disregard this message.\n\n"
        "Thank you,\nElite Prep Suwanee\n")
    html = (
        '<div style="font-family:-apple-system,Segoe UI,Arial,sans-serif;'
        'font-size:14px;color:#222">'
        f"<p>Hi {escape(teacher_first_name)},</p>"
        f"<p>The tutoring report for <b>{escape(session.student)}</b> "
        f"({escape(day)}, {escape(span)}{escape(subject_part)}) hasn't been "
        "submitted yet.</p>"
        f'<p><a href="{escape(config.TEACHER_FORM_URL)}">Submit the report</a></p>'
        "<p>If you have already submitted it, please disregard this message.</p>"
        "<p>Thank you,<br>Elite Prep Suwanee</p></div>")
    return subject, text, html


# --- The job ----------------------------------------------------------------

def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv
    now = datetime.now(ZoneInfo(config.LOCAL_TZ))

    try:
        creds = default_credentials()
        # Fetch by start time, generously: a session that started well before
        # the lookback window can still have ended inside it.
        window_start = now - timedelta(hours=config.REMINDER_LOOKBACK_HOURS + 12)
        sessions = fetch_sessions(creds, config.CALENDAR_ID, window_start, now)
        reports = [e.get("report", {}) for e in store.load_all()]
        teachers = parse_teachers(store.read_tab(config.TEACHERS_SHEET_NAME))
        already = reminder_log.reminded_event_ids()
    except Exception as e:
        print(e, file=sys.stderr)
        return 1

    due = sessions_due(sessions, now)
    print(f"[{now:%Y-%m-%d %H:%M}] {len(sessions)} session(s) on the calendar, "
          f"{len(due)} ended {config.REMINDER_DELAY_MINUTES}+ min ago.")
    if not teachers:
        print("The Teachers tab is empty, so nobody can be emailed.", file=sys.stderr)

    sent = failed = 0
    for s in due:
        label = f"{s.teacher} / {s.student} ({s.start:%m/%d %I:%M %p})"
        if s.event_id in already:
            print(f"  skip  {label}: already reminded")
            continue
        if any(report_matches_session(r, s) for r in reports):
            print(f"  ok    {label}: report submitted")
            continue
        teacher = find_teacher(teachers, s.teacher)
        if not teacher or not teacher.email:
            print(f"  ??    {label}: no email for teacher '{s.teacher}' on the "
                  "Teachers tab", file=sys.stderr)
            continue
        if not teacher.active:
            print(f"  skip  {label}: teacher marked inactive")
            continue

        subject, text, html = build_reminder(s, teacher.name.split()[0])
        if dry_run:
            print(f"  WOULD {label}: email {teacher.email} — {subject}")
            continue
        ok, msg = send_email(subject, text, html, teacher.email,
                             sender=config.SENDER_EMAIL, password=config.SENDER_PASSWORD,
                             host=config.SMTP_HOST, port=config.SMTP_PORT)
        if ok:
            reminder_log.record(s.event_id, s.teacher, s.student, s.end, teacher.email)
            sent += 1
            print(f"  SENT  {label} -> {teacher.email}")
        else:
            failed += 1
            print(f"  FAIL  {label}: {msg}", file=sys.stderr)

    print(f"Reminders sent: {sent}" + (f", failed: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
