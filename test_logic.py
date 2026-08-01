"""Quick checks for the report rendering, roster parsing and the report store."""

from datetime import date
from pathlib import Path
import tempfile
import threading

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


def test_store_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "reports.json"
        rid = store.add(path, SAMPLE)
        assert store.get(path, rid)["status"] == store.PENDING

        edited = {**SAMPLE, "student_name": "Eunho Lee"}
        store.update_report(path, rid, edited)
        assert store.get(path, rid)["report"]["student_name"] == "Eunho Lee"

        store.mark_sent(path, rid, "parent@x.com", "student@x.com")
        entry = store.get(path, rid)
        assert entry["status"] == store.SENT
        assert entry["sent_to"] == "parent@x.com"

        store.reopen(path, rid)
        assert store.get(path, rid)["status"] == store.PENDING
        assert store.delete(path, rid) and store.load_all(path) == []


def test_concurrent_submissions_do_not_drop_reports():
    """Two teachers hitting Submit at the same moment must both be stored.

    Saving is read-append-write, so without locking the later writer can save a
    list it read before the earlier one appended, silently losing a report.
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "reports.json"
        errors = []
        start = threading.Barrier(12)

        def submit(i: int) -> None:
            try:
                start.wait()            # maximise the overlap
                store.add(path, {**SAMPLE, "student_name": f"S{i:02d}"})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=submit, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, errors
        stored = sorted(e["report"]["student_name"] for e in store.load_all(path))
        assert stored == [f"S{i:02d}" for i in range(12)], f"lost: {stored}"


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
