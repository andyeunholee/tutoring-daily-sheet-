"""Teacher emails, from the Teachers tab of the reports spreadsheet.

    Teacher Name (as in calendar) | Email | Active

The name is matched on its first word against the calendar's "Teacher Name",
so "Joseph" covers "Joseph teacher" and "Joseph O'Hailey" alike.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.students import _truthy


@dataclass(frozen=True)
class Teacher:
    name: str
    email: str
    active: bool


def parse_teachers(values: list[list]) -> list[Teacher]:
    if not values:
        return []
    header = [str(c).strip().lower() for c in values[0]]

    def col(*prefixes: str) -> int:
        for i, h in enumerate(header):
            if any(h.startswith(p) for p in prefixes):
                return i
        return -1

    name_i = col("teacher name", "name")
    email_i = col("email")
    active_i = col("active")
    if name_i < 0:
        return []

    teachers = []
    for row in values[1:]:
        def cell(i: int) -> str:
            return str(row[i]).strip() if 0 <= i < len(row) else ""

        name = cell(name_i)
        if not name:
            continue
        active = True
        if active_i >= 0 and cell(active_i) != "":
            active = _truthy(cell(active_i))
        teachers.append(Teacher(name=name, email=cell(email_i), active=active))
    return teachers


def _first_word(name: str) -> str:
    parts = (name or "").split()
    return parts[0].lower() if parts else ""


def find_teacher(teachers: list[Teacher], calendar_name: str) -> Teacher | None:
    wanted = _first_word(calendar_name)
    if not wanted:
        return None
    for t in teachers:
        if _first_word(t.name) == wanted:
            return t
    return None
