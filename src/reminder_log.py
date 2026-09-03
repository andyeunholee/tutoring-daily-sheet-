"""Which sessions have already had a reminder, so nobody is nudged twice.

One row per reminder on the Reminders tab of the reports spreadsheet:

    event_id | sent_at | teacher | student | session_end | sent_to

The calendar's event id is unique per occurrence, so a weekly session gets a
fresh id every week and can be reminded about again the following week.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import config
from src import store

HEADER = ["event_id", "sent_at", "teacher", "student", "session_end", "sent_to"]


def ensure_tab() -> bool:
    return store.ensure_tab(config.REMINDERS_SHEET_NAME, HEADER)


def reminded_event_ids() -> set[str]:
    rows = store.read_tab(config.REMINDERS_SHEET_NAME)
    return {str(r[0]).strip() for r in rows[1:] if r and str(r[0]).strip()}


def record(event_id: str, teacher: str, student: str, session_end: datetime,
           sent_to: str) -> None:
    now = datetime.now(ZoneInfo(config.LOCAL_TZ)).isoformat(timespec="seconds")
    store.append_row(config.REMINDERS_SHEET_NAME, [
        event_id, now, teacher, student,
        session_end.isoformat(timespec="minutes"), sent_to])
