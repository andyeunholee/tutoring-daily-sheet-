"""Quick checks for the report rendering, roster parsing and the report store."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import config
import daily_reminder
from src import report as report_lib
from src import store
from src.mailer import invalid_addresses, split_addresses
from src.students import parse_students, find_student, RosterUnavailable

SAMPLE = report_lib.new_report(
    student_name="Eunho", class_date=date(2026, 2, 1), start_time="03:30 PM",
    teacher_name="Gabe", subject="Algebra 1",
    has_homework="Yes", homework_subject="Algebra 1", homework_due=date(2026, 2, 5),
    has_exam="No",
    lesson_content="Alg I - triangle\nAlg II - quadratics",
    attitude="Good attitude (Good)",
    quiz="No quiz conducted this session.",
    elite_homework="Practice problems 1-20",
)


def test_dates_render_in_the_email_formats():
    text = report_lib.render_text(SAMPLE)
    assert "Date: February 01, 2026" in text
    assert "Due Date: 02/05/2026" in text
    assert "Exam Date" not in text          # exam section hidden when has_exam == No
    assert report_lib.email_subject(SAMPLE) == "[Tutoring Report] Eunho - 02/01/2026"


def test_html_escapes_and_keeps_line_breaks():
    html = report_lib.render_html(
        {**SAMPLE, "lesson_content": "A & B\nsecond <line>"})
    assert "A &amp; B<br>second &lt;line&gt;" in html


def test_missing_dates_do_not_crash():
    blank = report_lib.new_report(student_name="X")
    assert "Date: " in report_lib.render_text(blank)
    report_lib.render_html(blank)


def test_report_survives_a_round_trip_through_a_sheet_row():
    entry = {
        "id": "abc123def456", "created_at": "2026-08-01T10:00:00-04:00",
        "status": store.PENDING, "sent_at": None, "sent_to": "", "sent_cc": "",
        "report": SAMPLE,
    }
    row = store.row_from_entry(entry)
    assert len(row) == len(store.COLUMNS)
    assert row[6] == "Eunho"            # student name is readable in the sheet
    assert row[7] == "2026-02-01"       # so is the class date
    assert store.entry_from_row(row) == entry


def test_rows_the_sheets_api_actually_returns():
    """Trailing empty cells come back missing, not blank, so short rows are normal."""
    short = store.entry_from_row(["abc", "2026-08-01T10:00:00-04:00", "pending"])
    assert short["status"] == "pending" and short["report"] == {}
    assert short["sent_at"] is None

    # Nothing here identifies a report; skip rather than build a broken entry.
    assert store.entry_from_row([]) is None
    assert store.entry_from_row(["", "", ""]) is None

    # A hand-edited sheet can leave unparseable JSON. Keep the row, drop the body.
    mangled = store.entry_from_row(["xyz", "", "sent", "", "", "", "", "", "{oops"])
    assert mangled["id"] == "xyz" and mangled["report"] == {}


ROSTER_ROWS = [
    ["Student Name", "Parent Name", "Parent Email", "Student Email", "Active"],
    ["Eunho Lee", "Mrs. Lee", "mom@x.com", "eunho@x.com", ""],
    ["Jihu Park", "Mr. Park", "dad@x.com", "", "No"],
    ["", "", "orphan@x.com", "", ""],          # blank name -> skipped
]


def test_roster_parsing_and_lookup():
    rows = parse_students(ROSTER_ROWS)
    assert [s.name for s in rows] == ["Eunho Lee", "Jihu Park"]
    assert rows[0].active and not rows[1].active
    assert find_student(rows, "eunho lee").parent_email == "mom@x.com"
    assert find_student(rows, "Eunho").student_email == "eunho@x.com"   # first name only
    assert find_student(rows, "Nobody") is None


NICKNAME_ROWS = [
    ["Student Name", "Parent Email"],
    ["Kyuheon (Andrew) Ahn", "andrew@x.com"],
    ["Suhyun Sean Byun", "sean@x.com"],
    ["MinYeong Heo", "min@x.com"],
    ["BuHyeon Heo", "bu@x.com"],
]


def test_roster_lookup_by_any_part_of_the_name():
    """Teachers type whatever they call the student, not the roster spelling."""
    rows = parse_students(NICKNAME_ROWS)
    assert find_student(rows, "Andrew").parent_email == "andrew@x.com"   # in parens
    assert find_student(rows, "Sean").parent_email == "sean@x.com"       # middle name
    assert find_student(rows, "andrew ahn").parent_email == "andrew@x.com"  # any order
    assert find_student(rows, "Kyuheon (Andrew) Ahn").parent_email == "andrew@x.com"
    assert find_student(rows, "MinYeong Heo").parent_email == "min@x.com"
    # A surname two students share stays ambiguous: better hand-typed than wrong.
    assert find_student(rows, "Heo") is None
    assert find_student(rows, "Nobody") is None


def test_roster_missing_header_explains_the_fix():
    try:
        parse_students([["Student Name", "Phone"], ["Eunho", "1"]])
    except RosterUnavailable as e:
        assert "Parent Email" in str(e)
    else:
        raise AssertionError("missing Parent Email header should raise")


def test_reminder_lists_what_is_waiting_and_for_how_long():
    now = datetime(2026, 8, 7, 11, 0, tzinfo=ZoneInfo("America/New_York"))

    def waiting(name, created):
        return {"id": name, "created_at": created, "status": store.PENDING,
                "report": {**SAMPLE, "student_name": name,
                           "class_date": "2026-08-01", "teacher_name": "Gabe"}}

    subject, text, html = daily_reminder.build_reminder([
        waiting("Zena", "2026-08-01T17:07:55-04:00"),
        waiting("Andrew", "2026-08-07T09:00:00-04:00"),
    ], now)

    assert "2 reports" in subject
    assert "Zena" in text and "Andrew" in text
    assert "waiting 5 day(s)" in text          # submitted Aug 1, now Aug 7
    assert "submitted today" in text
    assert config.REVIEW_APP_URL in text
    assert "<td" in html and "Zena" in html


def test_reminder_survives_names_that_look_like_markup():
    now = datetime(2026, 8, 7, 11, 0, tzinfo=ZoneInfo("America/New_York"))
    entry = {"id": "x", "created_at": "not a timestamp", "status": store.PENDING,
             "report": {**SAMPLE, "student_name": "<script>", "teacher_name": "A & B"}}
    _, text, html = daily_reminder.build_reminder([entry], now)
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "A &amp; B" in html
    assert "submitted today" in text           # unreadable timestamp must not crash


def test_address_parsing():
    assert split_addresses("a@x.com, b@y.com; c@z.com") == \
        ["a@x.com", "b@y.com", "c@z.com"]
    assert invalid_addresses("a@x.com, nope") == ["nope"]
    assert invalid_addresses("") == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS  {name}")
    print("\nAll checks passed.")
