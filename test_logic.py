"""Quick checks for the report rendering, roster parsing and the report store."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import config
import daily_drafts
import remind_missing_reports as remind
from src import calendar_events
from src import teachers as teachers_lib
from src import drafts as drafts_lib
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


def test_draft_carries_the_addresses_and_both_bodies():
    msg = drafts_lib.build_draft(
        "[Tutoring Report] Eunho - 02/01/2026", "plain text", "<p>html</p>",
        "mom@x.com, dad@x.com", "student@x.com", "me@school.com")
    assert msg["To"] == "mom@x.com, dad@x.com"
    assert msg["Cc"] == "student@x.com"
    assert msg["From"] == "me@school.com"
    types = [part.get_content_type() for part in msg.get_payload()]
    assert types == ["text/plain", "text/html"]     # HTML last so Gmail prefers it


def test_draft_with_no_known_address_still_gets_built():
    """A report whose student is not in the roster is still worth drafting."""
    msg = drafts_lib.build_draft("Subject", "text", "<p>h</p>", "", "",
                                 "me@school.com")
    assert msg["To"] is None and msg["Cc"] is None
    assert msg["Subject"] == "Subject"


def test_recipients_prefer_addresses_already_recorded():
    roster = parse_students(ROSTER_ROWS)
    from_roster = {"report": {"student_name": "Eunho Lee"}}
    assert daily_drafts.recipients_for(from_roster, roster) == (
        "mom@x.com", "eunho@x.com")

    # The director corrected the address once; do not overwrite it from the roster.
    corrected = {"sent_to": "grandma@x.com", "sent_cc": "",
                 "report": {"student_name": "Eunho Lee"}}
    assert daily_drafts.recipients_for(corrected, roster) == ("grandma@x.com", "")

    unknown = {"report": {"student_name": "Nobody At All"}}
    assert daily_drafts.recipients_for(unknown, roster) == ("", "")


def _session(**kw) -> calendar_events.Session:
    tz = ZoneInfo("America/New_York")
    base = dict(event_id="evt1", teacher="Joseph", student="Kyuheon (Andrew) Ahn",
                subject="English", canceled=False,
                start=datetime(2026, 8, 29, 13, 0, tzinfo=tz),
                end=datetime(2026, 8, 29, 14, 30, tzinfo=tz))
    base.update(kw)
    return calendar_events.Session(**base)


def test_calendar_titles_parse_into_sessions():
    p = calendar_events.parse_summary(
        " [TUT] Type: In-Person (Room #1), Teacher Name: Joseph teacher, "
        "Student Name: Kyuheon (Andrew) Ahn, Subject:  English ")
    assert p == {"teacher": "Joseph", "student": "Kyuheon (Andrew) Ahn",
                 "subject": "English", "canceled": False}
    c = calendar_events.parse_summary(
        "canceled by student: [TUT] Type: ONLINE, Teacher Name:  Jeongbeen teacher, "
        "Student Name: Bill, Subject: SAT Math & Calculus")
    assert c["canceled"] and c["teacher"] == "Jeongbeen"
    assert c["subject"] == "SAT Math & Calculus"
    # Group classes and to-do notes on the same calendar are not sessions.
    assert calendar_events.parse_summary(
        "[ CLS ]: SAT Weekend class- English : room #5] Joseph Teacher") is None
    assert calendar_events.parse_summary("매일 튜터링 이후에 보고서를 제출할것.") is None
    assert calendar_events.parse_summary("") is None


def test_a_report_is_matched_to_its_session_the_way_teachers_type():
    s = _session()
    ok = {"class_date": "2026-08-29", "teacher_name": "Joseph O'Hailey",
          "student_name": "Andrew"}
    assert remind.report_matches_session(ok, s)
    assert remind.report_matches_session({**ok, "student_name": "kyuheon (andrew) ahn"}, s)
    assert not remind.report_matches_session({**ok, "class_date": "2026-08-28"}, s)
    assert not remind.report_matches_session({**ok, "teacher_name": "Jeongbeen"}, s)
    assert not remind.report_matches_session({**ok, "student_name": "Zena"}, s)
    assert not remind.report_matches_session({**ok, "student_name": "Kim Ahn"}, s)
    # A typo means no match, and therefore a reminder. Documented, not solved.
    assert not remind.report_matches_session({**ok, "student_name": "Andrw"}, s)


def test_only_sessions_that_ended_an_hour_ago_are_due():
    tz = ZoneInfo("America/New_York")
    now = datetime(2026, 8, 29, 16, 0, tzinfo=tz)
    just_ended = _session(event_id="a", end=datetime(2026, 8, 29, 15, 30, tzinfo=tz))
    due = _session(event_id="b", end=datetime(2026, 8, 29, 14, 30, tzinfo=tz))
    canceled = _session(event_id="c", end=datetime(2026, 8, 29, 14, 0, tzinfo=tz),
                        canceled=True)
    ancient = _session(event_id="d", end=datetime(2026, 8, 29, 9, 0, tzinfo=tz))
    picked = remind.sessions_due([just_ended, due, canceled, ancient], now)
    assert [s.event_id for s in picked] == ["b"]


def test_teachers_tab_and_lookup():
    rows = [["Teacher Name (as in calendar)", "Email", "Active"],
            ["Joseph", "joseph@x.com", ""],
            ["Jeongbeen", "", ""],
            ["Peter", "peter@x.com", "No"]]
    ts = teachers_lib.parse_teachers(rows)
    assert teachers_lib.find_teacher(ts, "Joseph teacher").email == "joseph@x.com"
    assert teachers_lib.find_teacher(ts, "Jeongbeen").email == ""
    assert teachers_lib.find_teacher(ts, "Peter").active is False
    assert teachers_lib.find_teacher(ts, "Nobody") is None
    assert teachers_lib.parse_teachers([]) == []


def test_reminder_email_names_the_session_and_links_the_form():
    subject, text, html = remind.build_reminder(_session(), "Joseph")
    assert subject == ("Tutoring report needed: Kyuheon (Andrew) Ahn — "
                       "Aug 29, 1:00 PM–2:30 PM")
    assert "Hi Joseph," in text and config.TEACHER_FORM_URL in text
    assert "English" in text
    assert "hasn't been submitted" in html and "Submit the report" in html


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
