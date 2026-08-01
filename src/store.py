"""Submitted reports and their send status, kept in one JSON file.

Two Streamlit apps touch this file (the teacher form appends, the review app
edits and marks sent), so every write re-reads first and lands atomically.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PENDING = "pending"
SENT = "sent"

_LOCK_WAIT = 10.0       # seconds to wait for whoever is writing right now
_LOCK_STALE = 30.0      # a lock older than this was left behind by a dead app


@contextmanager
def _locked(path: Path):
    """Serialise read-modify-write on the store across apps and sessions.

    Saving is read-append-write, so two teachers submitting at the same moment
    would otherwise clobber each other; on Windows they collide on the shared
    .tmp file and the submission fails outright. Creating a lock file with
    O_CREAT|O_EXCL is the one atomic operation available on every filesystem
    this runs on, the Google Drive folder included.
    """
    lock = path.with_suffix(path.suffix + ".lock")
    deadline = time.monotonic() + _LOCK_WAIT
    fd = None
    while fd is None:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                stale = (time.time() - os.path.getmtime(lock)) > _LOCK_STALE
            except OSError:
                stale = False       # vanished under us; just retry
            if stale:
                # The holder died without cleaning up. Reclaim it rather than
                # block every future submission forever.
                try:
                    os.unlink(lock)
                except OSError:
                    pass
                continue
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Could not get the report store lock ({lock}). Another "
                    "submission may be stuck; delete that file if it persists.")
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(fd)
        try:
            os.unlink(lock)
        except OSError:
            pass


def _now_iso(tz: str) -> str:
    return datetime.now(ZoneInfo(tz)).isoformat(timespec="seconds")


def load_all(path: Path) -> list[dict]:
    """Every stored entry, newest first. A missing or corrupt file reads empty."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return sorted(data, key=lambda e: e.get("created_at", ""), reverse=True)


def _write_all(path: Path, entries: list[dict]) -> None:
    """Write the whole store atomically. Call inside _locked()."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    # This project lives on a Google Drive folder, where a write occasionally
    # fails for a moment even though nothing is wrong. A couple of retries
    # turns that into a hiccup instead of a lost report.
    for attempt in range(3):
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
            return
        except OSError:
            if attempt == 2:
                raise
            time.sleep(0.1)


def get(path: Path, entry_id: str) -> dict | None:
    for e in load_all(path):
        if e.get("id") == entry_id:
            return e
    return None


def add(path: Path, report: dict, tz: str = "America/New_York") -> str:
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
    with _locked(path):
        entries = load_all(path)
        entries.append(entry)
        _write_all(path, entries)
    return entry["id"]


def _mutate(path: Path, entry_id: str, change) -> bool:
    with _locked(path):
        entries = load_all(path)
        for e in entries:
            if e.get("id") == entry_id:
                change(e)
                _write_all(path, entries)
                return True
    return False


def update_report(path: Path, entry_id: str, report: dict) -> bool:
    """Save the director's edits without changing send status."""
    return _mutate(path, entry_id, lambda e: e.update(report=report))


def mark_sent(path: Path, entry_id: str, to: str, cc: str,
              tz: str = "America/New_York") -> bool:
    def change(e):
        e.update(status=SENT, sent_at=_now_iso(tz), sent_to=to, sent_cc=cc)
    return _mutate(path, entry_id, change)


def reopen(path: Path, entry_id: str) -> bool:
    """Put an already-sent report back in the pending list to send again."""
    def change(e):
        e.update(status=PENDING)
    return _mutate(path, entry_id, change)


def delete(path: Path, entry_id: str) -> bool:
    with _locked(path):
        entries = load_all(path)
        remaining = [e for e in entries if e.get("id") != entry_id]
        if len(remaining) == len(entries):
            return False
        _write_all(path, remaining)
    return True
