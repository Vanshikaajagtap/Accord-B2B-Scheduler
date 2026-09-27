from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from agent import build_accord_graph
from auth_test import (get_credentials, get_credentials_for_email,
                       list_authenticated_emails, is_email_authenticated,
                       _token_path, _ensure_tokens_dir)
from gmail_tool import get_gmail_service, send_email
from calendar_tool import get_calendar_service, create_calendar_event
from email_reader import list_inbox, read_email, search_emails, download_attachment
from document_parser import parse_attachments as parse_docs
from plugins import list_providers, get_provider
from google_auth_oauthlib.flow import Flow
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import json
import tempfile
import threading
import time

app = Flask(__name__)
CORS(app, supports_credentials=True)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")
OAUTH_REDIRECT_URI = "http://localhost:5001/api/participants/auth-callback"

# In-memory store: state -> email (cleared after use)
_pending_auth: dict[str, str] = {}

# In-memory store for auto-booking on reply
# threadId -> dict of details
_tracked_threads: dict[str, dict] = {}

accord_graph = build_accord_graph()

def start_polling_loop():
    def poll_gmail():
        llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)
        while True:
            time.sleep(30)
            if not _tracked_threads:
                continue
                
            try:
                creds = get_credentials()
                gmail = get_gmail_service(creds)
                
                keys = list(_tracked_threads.keys())
                for thread_id in keys:
                    data = _tracked_threads[thread_id]
                    # Check if there is a new message in this thread from the client
                    client_email = data.get("client_email", "")
                    query = f"thread:{thread_id} from:{client_email}"
                    results = search_emails(gmail, query=query, max_results=5)
                    
                    if not results:
                        continue
                        
                    # Filter out the original source email if they just replied
                    reply_msg = None
                    for msg in results:
                        # Assuming the most recent one that is from the client is the reply
                        if msg["id"] != data.get("source_email_id"):
                            reply_msg = msg
                            break
                            
                    if not reply_msg:
                        continue
                        
                    # We have a new reply!
                    print(f"Reply detected for thread {thread_id}!")
                    email_data = read_email(gmail, reply_msg["id"])
                    body = email_data.get("body_text", "")
                    
                    # Ask Gemini which slot they chose
                    slots = data.get("slots", [])
                    slots_str = "\n".join([f"Option {i+1}: {s.get('start')} to {s.get('end')}" for i, s in enumerate(slots)])
                    
                    prompt = f"A client replied to our meeting proposal. Our proposed slots were:\n{slots_str}\n\nClient reply:\n{body}\n\nExtract the confirmed time slot based on their reply. Return ONLY a JSON object with 'start' and 'end' keys containing the exact ISO timestamps from the options, or null if they didn't explicitly confirm any option."
                    
                    response = llm.invoke(prompt)
                    content = response.content
                    if isinstance(content, list):
                        content = content[0]["text"] if isinstance(content[0], dict) else content[0]
                    content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    
                    try:
                        choice = json.loads(content)
                        if choice and choice.get("start") and choice.get("end"):
                            cal = get_calendar_service(creds)
                            create_calendar_event(
                                cal,
                                summary="Meeting via Accord",
                                attendees=data.get("participants", []) + [client_email],
                                start_time=choice["start"],
                                end_time=choice["end"],
                                timezone=data.get("timezone", "UTC")
                            )
                            print(f"Successfully auto-booked event for thread {thread_id} at {choice['start']}!")
                            # Stop tracking this thread since it's booked
                            del _tracked_threads[thread_id]
                        else:
                            print(f"Gemini couldn't find a confirmed slot for thread {thread_id} in the reply.")
                    except json.JSONDecodeError:
                        print(f"Could not parse JSON from Gemini response for thread {thread_id}.")
            except Exception as e:
                print(f"Polling loop error: {e}")

    threading.Thread(target=poll_gmail, daemon=True).start()


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
        "unauthenticated_participants": result.get("unauthenticated_participants", []),
        "source_email_body": result.get("source_email_body", ""),
        "source_documents": result.get("source_documents", []),
    })


# ---------------------------------------------------------------------------
# Email Reading Endpoints
# ---------------------------------------------------------------------------


@app.route("/api/emails", methods=["GET"])
def email_list():
    """List recent emails from the authenticated inbox.

    Query params:
        max_results (int): Max emails to return (default 20).
        query (str): Optional Gmail search query.
        email (str): Optional — use a specific participant's credentials.
    """
    try:
        creds = get_credentials()
        service = get_gmail_service(creds)
        max_results = int(request.args.get("max_results", 20))
        query = request.args.get("query", None)
        emails = list_inbox(service, max_results=max_results, query=query)
        return jsonify({"emails": emails, "count": len(emails)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/emails/<message_id>", methods=["GET"])
def email_detail(message_id):
    """Read a single email by ID, including body text and attachment metadata."""
    try:
        creds = get_credentials()
        service = get_gmail_service(creds)
        email_data = read_email(service, message_id)
        return jsonify(email_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/emails/<message_id>/attachments/<attachment_id>", methods=["GET"])
def email_attachment_download(message_id, attachment_id):
    """Download a specific attachment. The filename is passed as a query param."""
    try:
        creds = get_credentials()
        service = get_gmail_service(creds)
        filename = request.args.get("filename", "attachment")
        data = download_attachment(service, message_id, attachment_id)
        return (
            data,
            200,
            {
                "Content-Type": "application/octet-stream",
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/emails/<message_id>/parse", methods=["GET"])
def email_parse_attachments(message_id):
    """Read an email and parse all its document attachments, returning extracted text."""
    try:
        creds = get_credentials()
        service = get_gmail_service(creds)
        email_data = read_email(service, message_id)
        docs = parse_docs(email_data.get("attachments", []))
        return jsonify({
            "email_id": message_id,
            "subject": email_data.get("subject", ""),
            "body": email_data.get("body_text", ""),
            "documents": docs,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/emails/search", methods=["POST"])
def email_search():
    """Search emails using a Gmail query string."""
    data = request.json or {}
    query = data.get("query", "")
    max_results = data.get("max_results", 20)
    if not query:
        return jsonify({"error": "query is required"}), 400
    try:
        creds = get_credentials()
        service = get_gmail_service(creds)
        results = search_emails(service, query, max_results=max_results)
        return jsonify({"emails": results, "count": len(results)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/emails/parse-doc", methods=["POST"])
def parse_uploaded_doc():
    """Parse an uploaded document file and return extracted text.

    Expects a multipart/form-data upload with a 'file' field,
    or JSON with base64 'data' and 'filename' fields.
    """
    try:
        if "file" in request.files:
            f = request.files["file"]
            filename = f.filename
            data = f.read()
        else:
            body = request.json or {}
            import base64 as b64
            data = b64.b64decode(body.get("data", ""))
            filename = body.get("filename", "document.txt")

        from document_parser import parse_document
        text = parse_document(filename, data)
        return jsonify({"filename": filename, "text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Plugin Endpoints
# ---------------------------------------------------------------------------


@app.route("/api/plugins", methods=["GET"])
def plugins_list():
    """List all registered email provider plugins."""
    return jsonify({"plugins": list_providers()})


@app.route("/api/plugins/<provider_name>/inbox", methods=["GET"])
def plugin_inbox(provider_name):
    """List inbox using a specific provider plugin."""
    try:
        provider = get_provider(provider_name)
        max_results = int(request.args.get("max_results", 20))
        query = request.args.get("query", None)
        emails = provider.list_inbox(max_results=max_results, query=query)
        return jsonify({"provider": provider_name, "emails": emails, "count": len(emails)})
    except KeyError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/plugins/<provider_name>/read/<message_id>", methods=["GET"])
def plugin_read_email(provider_name, message_id):
    """Read a full email using a specific provider plugin."""
    try:
        provider = get_provider(provider_name)
        email_data = provider.read_email(message_id)
        return jsonify(email_data)
    except KeyError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/plugins/<provider_name>/send", methods=["POST"])
def plugin_send_email(provider_name):
    """Send an email via a specific provider plugin."""
    data = request.json or {}
    try:
        provider = get_provider(provider_name)
        result = provider.send_email(
            to=data.get("to", ""),
            subject=data.get("subject", ""),
            body=data.get("body", ""),
        )
        return jsonify({"success": True, "result": result})
    except KeyError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/approve", methods=["POST"])
def approve_and_send():
    data = request.json
    client_email = data.get("client_email", "")
    draft_reply = data.get("draft_reply", "")
    participants = data.get("participants", [])
    first_slot = data.get("first_slot", {})
    all_slots = data.get("slots", [first_slot] if first_slot else [])
    timezone = data.get("timezone", "UTC")
    source_email_id = data.get("source_email_id", "")

    results = {"email": None, "calendar": None}

    try:
        creds = get_credentials()
        gmail = get_gmail_service(creds)
        # Assuming send_email returns a dict with 'id' and 'threadId' (or we can get it from 'id')
        r = send_email(
            gmail,
            to=client_email,
            subject="Meeting Request - Available Times",
            body=draft_reply
        )
        
        # We need the threadId to track replies
        msg_id = r.get("id")
        # Let's fetch the message to get its threadId if not returned by send_email
        if "threadId" in r:
            thread_id = r["threadId"]
        else:
            msg = gmail.users().messages().get(userId="me", id=msg_id, format="minimal").execute()
            thread_id = msg.get("threadId", msg_id)

        # Track this thread for auto-booking
        _tracked_threads[thread_id] = {
            "client_email": client_email,
            "participants": participants,
            "slots": all_slots,
            "timezone": timezone,
            "source_email_id": source_email_id
        }

        results["email"] = {"success": True, "id": msg_id, "threadId": thread_id}
        # Do not book the calendar immediately - wait for reply!
        results["calendar"] = {"success": True, "status": "Waiting for client reply to auto-book."}
    except Exception as e:
        results["email"] = {"success": False, "error": str(e)}
        results["calendar"] = {"success": False, "error": "Email failed, not tracking for reply."}

    return jsonify(results)


if __name__ == "__main__":
    start_polling_loop()
    app.run(host="0.0.0.0", port=5001, debug=True)
