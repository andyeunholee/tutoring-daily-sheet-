"""Authentication for Google APIs.

Two ways in, tried in order:

1. A service account key, from Streamlit secrets when deployed or a local
   service_account.json. This is the only one that works on a server, where
   nobody can click through a consent screen.
2. The browser consent flow, for local runs with no key configured.

A service account is its own Google identity, so any spreadsheet it touches
has to be shared with its client_email address.
"""

import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow

DEFAULT_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_SECRET = "gcp_service_account"


def _from_streamlit_secrets(scopes: list[str]):
    """The deployed path: a [gcp_service_account] block in Streamlit secrets."""
    try:
        import streamlit as st

        if SERVICE_ACCOUNT_SECRET not in st.secrets:
            return None
        info = dict(st.secrets[SERVICE_ACCOUNT_SECRET])
    except Exception:
        return None
    return ServiceAccountCredentials.from_service_account_info(info, scopes=scopes)


def _from_service_account_file(path: str, scopes: list[str]):
    if not path or not os.path.exists(path):
        return None
    return ServiceAccountCredentials.from_service_account_file(path, scopes=scopes)


def default_credentials():
    """Credentials for this project, wherever it happens to be running."""
    import config

    return get_credentials(
        str(config.CREDENTIALS_PATH), str(config.TOKEN_PATH), config.SCOPES,
        str(config.SERVICE_ACCOUNT_PATH))


def _covers(granted: list[str], wanted: list[str]) -> bool:
    """True when the granted scopes already permit everything wanted.

    A write scope implies its read-only form: a token holding
    ".../auth/spreadsheets" can obviously satisfy a request for
    ".../auth/spreadsheets.readonly". Without this, a perfectly usable token
    is thrown away and the user is dragged through the consent screen again.
    """
    have = set(granted)
    for scope in wanted:
        if scope in have:
            continue
        if scope.endswith(".readonly") and scope[: -len(".readonly")] in have:
            continue
        return False
    return True


def _load_token(token_path: str, scopes: list[str]) -> Credentials | None:
    """Load a stored token, keeping it if its scopes cover what we need."""
    try:
        with open(token_path, encoding="utf-8") as f:
            granted = json.load(f).get("scopes") or []
    except (OSError, ValueError):
        return None
    if not _covers(granted, scopes):
        return None
    # Hand google-auth the scopes actually on the token, so it does not
    # consider the credentials mis-scoped.
    return Credentials.from_authorized_user_file(token_path, granted)


def get_credentials(
    credentials_path: str = "credentials.json",
    token_path: str = "token.json",
    scopes: list[str] | None = None,
    service_account_path: str = "service_account.json",
):
    """Authenticate and return valid Google API credentials.

    A service account key wins when one is configured; otherwise this falls
    back to the stored OAuth token, refreshing or re-consenting as needed.
    """
    scopes = scopes or DEFAULT_SCOPES

    sa = (_from_streamlit_secrets(scopes)
          or _from_service_account_file(service_account_path, scopes))
    if sa is not None:
        return sa

    creds = _load_token(token_path, scopes) if os.path.exists(token_path) else None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
            creds = flow.run_local_server(
                port=0,
                authorization_prompt_message=(
                    "Sign in with your PERSONAL Google account "
                    "(andyeunholee@gmail.com), not the eliteprep.com work account "
                    "- the work account is blocked by its Workspace admin.\n"
                    "Opening the browser..."
                ),
            )

        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return creds
