"""Central configuration: settings, paths and Google auth constants.

Settings come from Streamlit secrets when deployed and from .env when running
locally, so the same code runs in both places without edits.
"""

import os
import shutil
import tempfile
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def setting(name: str, default: str = "") -> str:
    """One setting, from Streamlit secrets if present, else .env.

    st.secrets raises rather than returns empty when no secrets file exists,
    which is the normal case locally, so treat any failure as "not set there".
    """
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, default)


def _ensure_local_ca_bundle() -> None:
    """Mirror certifi's CA bundle onto local disk and point TLS at the copy.

    OpenSSL cannot load a CA bundle that lives on the Google Drive virtual
    filesystem: every HTTPS handshake dies with SSLEOFError even though the
    bytes are identical to a working copy. Since this project lives under
    H:\\My Drive, the venv's certifi bundle is on that filesystem.
    """
    try:
        import certifi
    except ImportError:
        return
    src = Path(certifi.where())
    local_root = Path(os.getenv("LOCALAPPDATA") or tempfile.gettempdir())
    try:
        if src.is_relative_to(local_root):
            return
    except (AttributeError, ValueError):
        pass
    dst = local_root / "TutoringDailySheet" / "cacert.pem"
    try:
        if not dst.exists() or dst.stat().st_size != src.stat().st_size:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    except OSError:
        return
    os.environ.setdefault("SSL_CERT_FILE", str(dst))
    os.environ.setdefault("REQUESTS_CA_BUNDLE", str(dst))


_ensure_local_ca_bundle()

# --- Google API auth ---
# Deployed, the apps authenticate as a service account (no browser available).
# Locally they fall back to the browser consent flow if no key is configured.
SERVICE_ACCOUNT_PATH = BASE_DIR / "service_account.json"
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token_tutoring.json"
# Writing the report store needs more than read-only; the missing-report
# reminder reads the tutoring calendar. If you change this, delete
# token_tutoring.json so the consent flow runs again.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar.readonly",
]

# --- Student roster Google Sheet ---
# The docs.google.com/spreadsheets/d/<ID>/edit part of the sheet URL.
STUDENTS_SPREADSHEET_ID = setting("STUDENTS_SPREADSHEET_ID")
STUDENTS_RANGE = "Students!A1:Z"

# --- Report store ---
# Deployed, reports live in a Google Sheet: the cloud filesystem is wiped on
# every restart, so a local file would lose them. Left unset, the apps fall
# back to the JSON file, which is what local runs use.
REPORTS_SPREADSHEET_ID = setting("REPORTS_SPREADSHEET_ID")
REPORTS_SHEET_NAME = "Reports"
REPORTS_PATH = BASE_DIR / "pending_reports.json"
RECORDS_CSV = BASE_DIR / "tutoring_records.csv"

# --- Missing-report reminder ---
# The calendar holding the "[TUT] ..." sessions. It has to be shared with the
# service account ("See all event details"), exactly like the spreadsheets.
CALENDAR_ID = setting("CALENDAR_ID", "andy.lee@eliteprep.com")
# Where a teacher goes to submit; the reminder email links here.
TEACHER_FORM_URL = setting(
    "TEACHER_FORM_URL", "https://3rptsszzfugdsemkjhfugt.streamlit.app/")
# Both tabs live in the reports spreadsheet, which the service account can edit.
TEACHERS_SHEET_NAME = "Teachers"
REMINDERS_SHEET_NAME = "Reminders"
REMINDER_DELAY_MINUTES = 60      # how long after a session ends before nudging
REMINDER_LOOKBACK_HOURS = 6      # sessions older than this are left alone

# --- Email ---
SENDER_EMAIL = setting("SENDER_EMAIL")
SENDER_PASSWORD = setting("SENDER_PASSWORD")
RECEIVER_EMAIL = setting("RECEIVER_EMAIL")
SMTP_HOST = setting("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(setting("SMTP_PORT", "587"))

# --- Review app ---
# Required once the app is reachable from the internet: it shows every parent's
# address and can send mail as SENDER_EMAIL.
ADMIN_PASSWORD = setting("ADMIN_PASSWORD")

LOCAL_TZ = "America/New_York"
