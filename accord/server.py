from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from agent import build_accord_graph
from auth_test import (get_credentials, get_credentials_for_email,
                       list_authenticated_emails, is_email_authenticated,
                       _token_path, _ensure_tokens_dir)
from gmail_tool import get_gmail_service, send_email
from calendar_tool import get_calendar_service, create_calendar_event
from google_auth_oauthlib.flow import Flow
import os
import json
import threading

app = Flask(__name__)
CORS(app, supports_credentials=True)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send"
]
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")
OAUTH_REDIRECT_URI = "http://localhost:5001/api/participants/auth-callback"

# In-memory store: state -> email (cleared after use)
_pending_auth: dict[str, str] = {}

accord_graph = build_accord_graph()


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/participants", methods=["GET"])
def get_participants():
    emails = list_authenticated_emails()
    return jsonify({"participants": emails})


@app.route("/api/participants/check", methods=["POST"])
def check_participant():
    data = request.json
    email = data.get("email", "")
    authenticated = is_email_authenticated(email)
    return jsonify({"email": email, "authenticated": authenticated})


@app.route("/api/participants/auth-start", methods=["POST"])
def auth_start():
    """Return the Google OAuth authorization URL for the frontend to redirect to."""
    data = request.json or {}
    email = data.get("email", "").strip()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=OAUTH_REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        login_hint=email
    )
    _pending_auth[state] = email
    return jsonify({"auth_url": auth_url, "state": state})


@app.route("/api/participants/auth-callback", methods=["GET"])
def auth_callback():
    """Handle the OAuth redirect from Google, save the token, then close the tab."""
    state = request.args.get("state", "")
    code = request.args.get("code", "")
    error = request.args.get("error", "")

    if error:
        return f"<h2>Authentication failed: {error}</h2><script>window.close();</script>", 400

    email = _pending_auth.pop(state, None)
    if not email:
        return "<h2>Unknown or expired auth session.</h2>", 400

    try:
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri=OAUTH_REDIRECT_URI,
            state=state
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        _ensure_tokens_dir()
        path = _token_path(email)
        with open(path, "w") as f:
            f.write(creds.to_json())
        return (
            f"<h2 style='font-family:sans-serif;color:#22c55e'>✓ {email} authenticated!</h2>"
            f"<p style='font-family:sans-serif'>You can close this tab and return to Accord.</p>"
            f"<script>setTimeout(()=>window.close(),2000);</script>"
        )
    except Exception as e:
        return f"<h2>Error saving credentials: {e}</h2>", 500


@app.route("/api/schedule", methods=["POST"])
def run_schedule():
    data = request.json
    raw_request = data.get("raw_request", "")
    if not raw_request:
        return jsonify({"error": "raw_request is required"}), 400

    try:
        result = accord_graph.invoke({
            "raw_request": raw_request,
            "participants": [],
            "duration_mins": 30,
            "timeframe_days": 5,
            "timezone": "UTC",
            "preferred_time": "any",
            "excluded_days": [],
            "free_slots": [],
            "draft_reply": "",
            "retry_count": 0,
            "is_compromise": False,
            "unauthenticated_participants": []
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "participants": result.get("participants", []),
        "duration_mins": result.get("duration_mins", 30),
        "timeframe_days": result.get("timeframe_days", 5),
        "timezone": result.get("timezone", "UTC"),
        "preferred_time": result.get("preferred_time", "any"),
        "free_slots": result.get("free_slots", []),
        "draft_reply": result.get("draft_reply", ""),
        "is_compromise": result.get("is_compromise", False),
        "unauthenticated_participants": result.get("unauthenticated_participants", [])
    })


@app.route("/api/approve", methods=["POST"])
def approve_and_send():
    data = request.json
    client_email = data.get("client_email", "")
    draft_reply = data.get("draft_reply", "")
    participants = data.get("participants", [])
    first_slot = data.get("first_slot", {})
    timezone = data.get("timezone", "UTC")

    results = {"email": None, "calendar": None}

    try:
        creds = get_credentials()
        gmail = get_gmail_service(creds)
        r = send_email(
            gmail,
            to=client_email,
            subject="Meeting Request - Available Times",
            body=draft_reply
        )
        results["email"] = {"success": True, "id": r["id"]}
    except Exception as e:
        results["email"] = {"success": False, "error": str(e)}

    if first_slot:
        try:
            creds = get_credentials()
            cal = get_calendar_service(creds)
            event = create_calendar_event(
                cal,
                summary="Meeting via Accord",
                attendees=participants + [client_email],
                start_time=first_slot.get("start", ""),
                end_time=first_slot.get("end", ""),
                timezone=timezone
            )
            results["calendar"] = {"success": True, "link": event.get("htmlLink", "")}
        except Exception as e:
            results["calendar"] = {"success": False, "error": str(e)}

    return jsonify(results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
