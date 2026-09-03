"""Tutoring sessions, read from the director's Google Calendar.

Sessions are the events whose title starts with "[TUT]", written in one fixed
shape by the director:

    [TUT] Type: ONLINE, Teacher Name: Joseph teacher, Student Name: Zena, Subject: College Essay
    canceled by student: [TUT] Type: ..., Teacher Name: ..., Student Name: Bill, Subject: ...

Anything else on the calendar ("[ CLS ]" group classes, to-do notes) is not a
session and is ignored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class CalendarUnavailable(RuntimeError):
    """The calendar cannot be read, with a message that says how to fix it."""


@dataclass(frozen=True)
class Session:
    event_id: str
    teacher: str        # as written in the calendar, "teacher" suffix dropped
    student: str        # as written in the calendar
    subject: str
    start: datetime
    end: datetime
    canceled: bool


_SUMMARY = re.compile(
    r"""^\s*
        (?P<cancel>cancell?ed\s+by\s+[^:]*:\s*)?
        \[\s*TUT\s*\]\s*
        (?:Type\s*:\s*(?P<type>.*?),\s*)?
        Teacher\s*Name\s*:\s*(?P<teacher>.*?),\s*
        Student\s*Name\s*:\s*(?P<student>.*?),\s*
        Subject\s*:\s*(?P<subject>.*?)\s*$""",
    re.IGNORECASE | re.VERBOSE)

_TEACHER_SUFFIX = re.compile(r"\s+teacher\s*$", re.IGNORECASE)


def parse_summary(summary: str) -> dict | None:
    """Pull teacher, student, subject and cancellation out of an event title.

    None for anything that is not a "[TUT]" session.
    """
    m = _SUMMARY.match(summary or "")
    if not m:
        return None
    return {
        "teacher": _TEACHER_SUFFIX.sub("", m.group("teacher").strip()),
        "student": " ".join(m.group("student").split()),
        "subject": m.group("subject").strip(),
        "canceled": bool(m.group("cancel")),
    }


def _when(field: dict) -> datetime | None:
    """Timed events only: an all-day entry has no dateTime and is never a session."""
    value = field.get("dateTime")
    return datetime.fromisoformat(value) if value else None


def fetch_sessions(creds, calendar_id: str, time_min: datetime,
                   time_max: datetime) -> list[Session]:
    """Every [TUT] session that starts inside the window, recurrences expanded."""
    svc = build("calendar", "v3", credentials=creds)
    try:
        resp = svc.events().list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat(), timeMax=time_max.isoformat(),
            singleEvents=True, orderBy="startTime", maxResults=250).execute()
    except HttpError as e:
        status = getattr(getattr(e, "resp", None), "status", None)
        hint = {
            404: ("The calendar is not visible to the service account. Share it "
                  "with the client_email in the service account key "
                  '("See all event details").'),
            403: "The service account is not allowed to read this calendar.",
        }.get(status, "")
        raise CalendarUnavailable(
            f"Reading calendar {calendar_id} failed (HTTP {status}). {hint}".strip()
        ) from e

    sessions = []
    for ev in resp.get("items", []):
        if ev.get("status") == "cancelled":
            continue
        parsed = parse_summary(ev.get("summary", ""))
        if not parsed:
            continue
        start, end = _when(ev.get("start", {})), _when(ev.get("end", {}))
        if not start or not end:
            continue
        sessions.append(Session(event_id=ev["id"], start=start, end=end, **parsed))
    return sessions
