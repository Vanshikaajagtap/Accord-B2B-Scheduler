from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
import os
import json

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]

TOKENS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens")


def _ensure_tokens_dir():
    os.makedirs(TOKENS_DIR, exist_ok=True)


def _token_path(email):
    safe = email.replace("@", "_at_").replace(".", "_")
    return os.path.join(TOKENS_DIR, f"{safe}.json")


def get_credentials():
    _ensure_tokens_dir()
    creds = None
    legacy = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
    if os.path.exists(legacy):
        creds = Credentials.from_authorized_user_file(legacy, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                os.remove(legacy)
                creds = None
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open(legacy, "w") as f:
            f.write(creds.to_json())
    return creds


def get_credentials_for_email(email):
    _ensure_tokens_dir()
    path = _token_path(email)
    creds = None
    if os.path.exists(path):
        creds = Credentials.from_authorized_user_file(path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(path, "w") as f:
                    f.write(creds.to_json())
            except RefreshError:
                os.remove(path)
                return None
        else:
            return None
    return creds


def authenticate_email(email):
    _ensure_tokens_dir()
    path = _token_path(email)
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)
    with open(path, "w") as f:
        f.write(creds.to_json())
    return creds


def list_authenticated_emails():
    _ensure_tokens_dir()
    emails = []
    for filename in os.listdir(TOKENS_DIR):
        if not filename.endswith(".json"):
            continue
        name = filename.removesuffix(".json")
        email = name.replace("_at_", "@").replace("_", ".", 1)
        parts = email.split("@")
        if len(parts) == 2:
            local = parts[0]
            domain = parts[1].replace("_", ".")
            email = f"{local}@{domain}"
        emails.append(email)
    return emails


def is_email_authenticated(email):
    path = _token_path(email)
    if not os.path.exists(path):
        return False
    creds = get_credentials_for_email(email)
    return creds is not None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        email = sys.argv[1]
        print(f"Authenticating {email}...")
        authenticate_email(email)
        print(f"Token saved for {email}")
    else:
        creds = get_credentials()
        print("Auth successful! token.json created.")
    authenticated = list_authenticated_emails()
    if authenticated:
        print(f"Authenticated accounts: {authenticated}")