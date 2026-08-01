"""Central configuration: paths, Google auth constants, .env loading."""

import os
import shutil
import tempfile
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


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
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token_tutoring.json"
# NOTE: if you ever change SCOPES, delete token_tutoring.json and re-consent.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# --- Student roster Google Sheet ---
# The docs.google.com/spreadsheets/d/<ID>/edit part of the sheet URL.
STUDENTS_SPREADSHEET_ID = os.getenv("STUDENTS_SPREADSHEET_ID", "")
STUDENTS_RANGE = "Students!A1:Z"

# --- Email ---
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# --- Review app ---
REPORTS_PATH = BASE_DIR / "pending_reports.json"
RECORDS_CSV = BASE_DIR / "tutoring_records.csv"

LOCAL_TZ = "America/New_York"
