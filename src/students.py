"""Load the student roster Google Sheet, mapping columns by header name.

Expected "Students" tab layout (row 1 = headers, order does not matter):

    Student Name | Parent Name | Parent Email | Student Email | Active

Only "Student Name" and "Parent Email" are required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class RosterUnavailable(RuntimeError):
    """Students tab missing/unreadable, with a message that says how to fix it."""


@dataclass(frozen=True)
class StudentRow:
    name: str
    parent_name: str
    parent_email: str
    student_email: str
    active: bool


def _truthy(v) -> bool:
    return str(v).strip().lower() not in ("false", "no", "0", "n", "x")


def _find_columns(header_row: list) -> dict[str, int]:
    cols: dict[str, int] = {}
    for i, h in enumerate(str(c).strip().lower() for c in header_row):
        if h in ("student name", "student", "name"):
            cols.setdefault("name", i)
        elif h in ("parent name", "guardian name"):
            cols.setdefault("parent_name", i)
        elif h in ("parent email", "guardian email", "parent e-mail"):
            cols.setdefault("parent_email", i)
        elif h in ("student email", "student e-mail"):
            cols.setdefault("student_email", i)
        elif h == "active":
            cols.setdefault("active", i)
    labels = {"name": "Student Name", "parent_email": "Parent Email"}
    missing = [labels[k] for k in ("name", "parent_email") if k not in cols]
    if missing:
        raise RosterUnavailable(
            "Students tab row 1 is missing header(s): " + ", ".join(missing)
            + ". Add the column header(s) exactly (e.g. 'Parent Email') and reload.")
    return cols


def parse_students(values: list[list]) -> list[StudentRow]:
    if not values:
        raise RosterUnavailable(
            "The Students tab is empty or missing. Check the spreadsheet ID and "
            "that the tab is named 'Students'.")
    cols = _find_columns(values[0])

    def cell(row: list, key: str) -> str:
        i = cols.get(key, -1)
        return str(row[i]).strip() if 0 <= i < len(row) else ""

    students = []
    for row in values[1:]:
        name = cell(row, "name")
        if not name:
            continue
        active = True
        if "active" in cols and cell(row, "active") != "":
            active = _truthy(cell(row, "active"))
        students.append(StudentRow(
            name=name,
            parent_name=cell(row, "parent_name"),
            parent_email=cell(row, "parent_email"),
            student_email=cell(row, "student_email"),
            active=active,
        ))
    return students


def _name_words(name: str) -> set[str]:
    """Name split into comparable words, punctuation dropped.

    "Kyuheon (Andrew) Ahn" -> {"kyuheon", "andrew", "ahn"}
    """
    return set(re.findall(r"[\w']+", (name or "").lower()))


def find_student(students: list[StudentRow], name: str) -> StudentRow | None:
    """Case-insensitive lookup by student name; exact match first, then by words.

    Teachers type whatever they call the student, which is often not how the
    roster spells it: "Andrew" or "Andrew Ahn" for "Kyuheon (Andrew) Ahn".
    So every word typed must appear somewhere in the student's name, in any
    order. Input matching two or more students (a shared surname, say) matches
    nothing, leaving the addresses to be entered by hand rather than guessed.
    """
    wanted = (name or "").strip().lower()
    if not wanted:
        return None
    for s in students:
        if s.name.strip().lower() == wanted:
            return s
    words = _name_words(wanted)
    if not words:
        return None
    matches = [s for s in students if words <= _name_words(s.name)]
    return matches[0] if len(matches) == 1 else None


def load_students(creds, spreadsheet_id: str, sheet_range: str) -> list[StudentRow]:
    try:
        svc = build("sheets", "v4", credentials=creds)
        resp = (svc.spreadsheets().values()
                .get(spreadsheetId=spreadsheet_id, range=sheet_range)
                .execute())
    except HttpError as e:
        raise RosterUnavailable(
            f"Could not read the Students tab (HTTP {e.resp.status}). Check that "
            "the spreadsheet ID is correct and that the Google account you "
            "consented with can open the roster spreadsheet.") from e
    return parse_students(resp.get("values", []))
