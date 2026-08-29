"""Prepare a Gmail draft for every tutoring report still waiting for parents.

Run on demand, from the Actions tab or a shell. It sends nothing. The messages
are left in the sender's drafts folder, addressed and filled in, for the
director to read over and send from Gmail.

    python daily_drafts.py             # prepare the drafts
    python daily_drafts.py --dry-run   # list what it would prepare, touch nothing
"""

from __future__ import annotations

import sys

import config
from src import drafts
from src import store


def _roster() -> list:
    """The student list, or an empty one. A missing roster is not fatal here:
    a draft with no To is still worth preparing, with the address left blank."""
    if not config.STUDENTS_SPREADSHEET_ID:
        return []
    try:
        from src.auth import default_credentials
        from src.students import load_students
        return load_students(default_credentials(), config.STUDENTS_SPREADSHEET_ID,
                             config.STUDENTS_RANGE)
    except Exception as e:
        print(f"Roster unavailable ({e}); drafts will have no addresses.",
              file=sys.stderr)
        return []


def recipients_for(entry: dict, roster: list) -> tuple[str, str]:
    """(to, cc) for a report: whatever was already recorded, else the roster."""
    from src.students import find_student

    to, cc = entry.get("sent_to", ""), entry.get("sent_cc", "")
    if to or cc:
        return to, cc
    match = find_student(roster, entry.get("report", {}).get("student_name", ""))
    if not match:
        return "", ""
    return match.parent_email, match.student_email


def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv

    try:
        waiting = [e for e in store.load_all() if e.get("status") == store.PENDING]
    except Exception as e:
        print(e, file=sys.stderr)
        return 1

    if not waiting:
        print("No reports are waiting. No drafts prepared.")
        return 0

    # Oldest first, so the drafts stack up in the order the lessons happened.
    waiting.sort(key=lambda e: e.get("created_at", ""))
    roster = _roster()

    prepared = []
    for entry in waiting:
        to, cc = recipients_for(entry, roster)
        msg = drafts.build_report_draft(
            entry.get("report", {}), to, cc, config.SENDER_EMAIL)
        prepared.append((entry, to, cc, msg))

    if dry_run:
        for entry, to, cc, msg in prepared:
            name = entry["report"].get("student_name") or "(no name)"
            print(f"  {name}: To={to or '(blank)'} Cc={cc or '(blank)'} "
                  f"| {msg['Subject']}")
        print(f"Would prepare {len(prepared)} draft(s).")
        return 0

    results = drafts.save_drafts(
        [p[3] for p in prepared],
        sender=config.SENDER_EMAIL, password=config.SENDER_PASSWORD)

    saved, failed, no_address = 0, 0, []
    for (entry, to, cc, _), (ok, message) in zip(prepared, results):
        name = entry["report"].get("student_name") or "(no name)"
        if not ok:
            failed += 1
            print(f"{name}: {message}", file=sys.stderr)
            continue
        saved += 1
        if not to:
            no_address.append(name)
        # Only after the draft exists, so a failure here is retried tomorrow.
        store.mark_drafted(entry["id"], to, cc)

    print(f"Prepared {saved} draft(s) in the Gmail drafts folder.")
    if no_address:
        print("No roster match, address left blank: " + ", ".join(no_address))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
