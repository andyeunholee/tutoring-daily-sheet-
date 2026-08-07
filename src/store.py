"""Submitted reports and their send status, kept in a Google Sheet.

A Sheet rather than a file on disk because the deployed apps run on a
filesystem that is wiped on every restart, which would take the pending
reports with it. It also removes the write race the local file had: rows are
appended by Google's servers, so two teachers submitting at the same moment
cannot overwrite one another.

One row per report. The full report is JSON in the last column; the columns
before it exist so the sheet stays readable at a glance.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

PENDING = "pending"
SENT = "sent"

COLUMNS = ["id", "created_at", "status", "sent_at", "sent_to", "sent_cc",
           "student_name", "class_date", "report_json"]
_LAST_COL = "I"          # COLUMNS is 9 wide; keep these in step


class StoreUnavailable(RuntimeError):
    """The reports Sheet is unreachable, with a message that says how to fix it."""


def _now_iso(tz: str) -> str:
    return datetime.now(ZoneInfo(tz)).isoformat(timespec="seconds")


# --- Row <-> entry, the pure part ----------------------------------------

def row_from_entry(entry: dict) -> list[str]:
    report = entry.get("report", {})
    return [
        entry.get("id", ""),
        entry.get("created_at", ""),
        entry.get("status", PENDING),
        entry.get("sent_at") or "",
        entry.get("sent_to", ""),
        entry.get("sent_cc", ""),
        str(report.get("student_name", "")),
        str(report.get("class_date", "")),
        json.dumps(report, ensure_ascii=False),
    ]


def entry_from_row(row: list) -> dict | None:
    """One sheet row as an entry, or None if it holds no usable report."""
    cells = [str(c) for c in row] + [""] * (len(COLUMNS) - len(row))
    entry_id = cells[0].strip()
    if not entry_id:
        return None
    try:
        report = json.loads(cells[8]) if cells[8] else {}
    except ValueError:
        report = {}
    if not isinstance(report, dict):
        report = {}
    return {
        "id": entry_id,
        "created_at": cells[1],
        "status": cells[2] or PENDING,
        "sent_at": cells[3] or None,
        "sent_to": cells[4],
        "sent_cc": cells[5],
        "report": report,
    }


# --- Talking to the Sheet -------------------------------------------------

@lru_cache(maxsize=1)
def _service():
    from src.auth import default_credentials
    return build("sheets", "v4", credentials=default_credentials())


def _explain(e: HttpError, what: str) -> StoreUnavailable:
    """Turn a bare HttpError into something that says what to go fix.

    Streamlit redacts exception text in deployed apps, so an unhandled
    HttpError reaches the user as "error details are in the logs" and nothing
    else. The status code is the whole diagnosis here, so say it out loud.
    """
    status = getattr(getattr(e, "resp", None), "status", None)
    hint = {
        403: ("The reports spreadsheet is not shared with the service account. "
              "Share it with the client_email in the service account key, as Editor."),
        404: ("No spreadsheet with that id is visible. Check "
              "REPORTS_SPREADSHEET_ID in the app's secrets."),
    }.get(status, "")
    return StoreUnavailable(f"{what} failed (HTTP {status}). {hint}".strip())


@lru_cache(maxsize=1)
def _tab() -> tuple[str, int]:
    """(tab title, sheet id) for the reports tab.

    Prefers the configured name and falls back to the first tab, so a sheet
    whose tab was left named "Untitled" still works.
    """
    import config
    try:
        meta = _service().spreadsheets().get(spreadsheetId=_sheet_id()).execute()
    except HttpError as e:
        raise _explain(e, "Opening the reports spreadsheet") from e
    sheets = meta.get("sheets", [])
    if not sheets:
        raise StoreUnavailable("The reports spreadsheet has no tabs.")
    for s in sheets:
        if s["properties"]["title"] == config.REPORTS_SHEET_NAME:
            return s["properties"]["title"], s["properties"]["sheetId"]
    first = sheets[0]["properties"]
    return first["title"], first["sheetId"]


def _values():
    return _service().spreadsheets().values()


def _sheet_id() -> str:
    import config
    if not config.REPORTS_SPREADSHEET_ID:
        raise StoreUnavailable(
            "REPORTS_SPREADSHEET_ID is not set. Add it to .env (locally) or to "
            "the app's secrets (deployed) so reports have somewhere to live.")
    return config.REPORTS_SPREADSHEET_ID


def _rows() -> list[list]:
    """Every data row, header excluded, paired with nothing else."""
    title, _ = _tab()
    try:
        resp = _values().get(
            spreadsheetId=_sheet_id(),
            range=f"'{title}'!A2:{_LAST_COL}").execute()
    except HttpError as e:
        raise _explain(e, "Reading the reports sheet") from e
    return resp.get("values", [])


# --- The API the apps use -------------------------------------------------

def load_all() -> list[dict]:
    """Every stored entry, newest first."""
    try:
        entries = [e for e in (entry_from_row(r) for r in _rows()) if e]
    except StoreUnavailable:
        raise               # already carries a diagnosis; do not bury it
    except Exception as e:
        # Cause unknown here — say so rather than guessing at permissions.
        raise StoreUnavailable(
            f"Reading the reports sheet failed: {type(e).__name__}: {e}") from e
    return sorted(entries, key=lambda e: e.get("created_at", ""), reverse=True)


def get(entry_id: str) -> dict | None:
    for e in load_all():
        if e.get("id") == entry_id:
            return e
    return None


def add(report: dict, tz: str = "America/New_York") -> str:
    """Store a freshly submitted report as pending and return its id."""
    entry = {
        "id": uuid.uuid4().hex[:12],
        "created_at": _now_iso(tz),
        "status": PENDING,
        "sent_at": None,
        "sent_to": "",
        "sent_cc": "",
        "report": report,
    }
    title, _ = _tab()
    try:
        _values().append(
            spreadsheetId=_sheet_id(),
            range=f"'{title}'!A:{_LAST_COL}",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row_from_entry(entry)]}).execute()
    except HttpError as e:
        raise _explain(e, "Saving the report") from e
    return entry["id"]


def _row_number(entry_id: str) -> tuple[int, dict] | tuple[None, None]:
    """1-based sheet row for an entry, counting the header."""
    for i, row in enumerate(_rows(), start=2):
        entry = entry_from_row(row)
        if entry and entry["id"] == entry_id:
            return i, entry
    return None, None


def _mutate(entry_id: str, change) -> bool:
    number, entry = _row_number(entry_id)
    if number is None:
        return False
    change(entry)
    title, _ = _tab()
    _values().update(
        spreadsheetId=_sheet_id(),
        range=f"'{title}'!A{number}:{_LAST_COL}{number}",
        valueInputOption="RAW",
        body={"values": [row_from_entry(entry)]}).execute()
    return True


def update_report(entry_id: str, report: dict) -> bool:
    """Save the director's edits without changing send status."""
    return _mutate(entry_id, lambda e: e.update(report=report))


def mark_sent(entry_id: str, to: str, cc: str,
              tz: str = "America/New_York") -> bool:
    def change(e):
        e.update(status=SENT, sent_at=_now_iso(tz), sent_to=to, sent_cc=cc)
    return _mutate(entry_id, change)


def reopen(entry_id: str) -> bool:
    """Put an already-sent report back in the pending list to send again."""
    return _mutate(entry_id, lambda e: e.update(status=PENDING))


def delete(entry_id: str) -> bool:
    number, _ = _row_number(entry_id)
    if number is None:
        return False
    _, sheet_id = _tab()
    _service().spreadsheets().batchUpdate(
        spreadsheetId=_sheet_id(),
        body={"requests": [{"deleteDimension": {"range": {
            "sheetId": sheet_id, "dimension": "ROWS",
            "startIndex": number - 1, "endIndex": number}}}]}).execute()
    return True
