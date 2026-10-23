"""
Email Reader — reads emails, searches inbox, and extracts attachments from Gmail.

Part of the Accord B2B Scheduler document-reading plugin.
"""

import base64
import json
import os
from typing import Optional


def _get_gmail_service(creds):
    """Build a Gmail API service from credentials."""
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=creds)


def list_inbox(service, max_results: int = 20, query: Optional[str] = None) -> list[dict]:
    """
    List recent emails from the inbox.

    Args:
        service: Gmail API service instance.
        max_results: Maximum number of messages to return.
        query: Optional Gmail search query string (e.g. "is:unread", "from:alice@co.com").

    Returns:
        List of dicts with keys: id, from, to, subject, snippet, date.
    """
    params = {"userId": "me", "maxResults": max_results}
    if query:
        params["q"] = query

    messages = service.users().messages().list(**params).execute().get("messages", [])

    emails = []
    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"]
        ).execute()

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        emails.append({
            "id": msg["id"],
            "threadId": msg.get("threadId"),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "snippet": msg.get("snippet", ""),
            "date": headers.get("Date", ""),
        })
    return emails


def read_email(service, message_id: str) -> dict:
    """
    Read the full content of a specific email, including body text and attachments.

    Returns:
        Dict with keys: id, from, to, subject, date, body_text, attachments (list).
        Each attachment has: filename, mimeType, size, data (base64-encoded), attachmentId.
    """
    msg = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()

    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    body_text = ""
    attachments = []

    def _extract_parts(part):
        nonlocal body_text
        mime = part.get("mimeType", "")
        filename = part.get("filename", "")

        if filename:
            attachments.append({
                "filename": filename,
                "mimeType": mime,
                "size": part.get("body", {}).get("size", 0),
                "data": part.get("body", {}).get("data", ""),
                "attachmentId": part.get("body", {}).get("attachmentId", ""),
            })
        elif mime == "text/plain" and part.get("body", {}).get("data"):
            body_text += base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        elif mime == "text/html" and not body_text and part.get("body", {}).get("data"):
            body_text += f"[HTML content — {len(part['body']['data'])} chars encoded]"

        for sub in part.get("parts", []):
            _extract_parts(sub)

    payload = msg.get("payload", {})
    _extract_parts(payload)

    return {
        "id": msg["id"],
        "threadId": msg.get("threadId"),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "body_text": body_text.strip(),
        "attachments": attachments,
    }


def download_attachment(service, message_id: str, attachment_id: str) -> bytes:
    """
    Download a specific attachment by its attachmentId.

    Returns:
        Raw bytes of the attachment content.
    """
    att = service.users().messages().attachments().get(
        userId="me", messageId=message_id, id=attachment_id
    ).execute()
    data = base64.urlsafe_b64decode(att["data"])
    return data


def save_attachment(service, message_id: str, attachment_id: str,
                    filename: str, save_dir: str) -> str:
    """
    Download and save an attachment to disk.

    Returns:
        The full file path where the attachment was saved.
    """
    os.makedirs(save_dir, exist_ok=True)
    data = download_attachment(service, message_id, attachment_id)
    path = os.path.join(save_dir, filename)
    with open(path, "wb") as f:
        f.write(data)
    return path


def search_emails(service, query: str, max_results: int = 20) -> list[dict]:
    """
    Search emails using a Gmail query string.

    Examples:
        "is:unread"
        "from:alice@co.com subject:proposal"
        "has:attachment filename:pdf"
        "after:2026/01/01 before:2026/06/01"
    """
    return list_inbox(service, max_results=max_results, query=query)
