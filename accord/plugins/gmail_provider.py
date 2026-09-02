"""
Gmail Provider Plugin

Implements the EmailProvider interface for Google Gmail.
Wraps the existing auth_test, gmail_tool, and email_reader modules.
"""

import base64
from typing import Optional

from auth_test import (
    get_credentials,
    get_credentials_for_email,
    list_authenticated_emails,
    is_email_authenticated,
)
from email_reader import (
    list_inbox as _list_inbox,
    read_email as _read_email,
    download_attachment as _download_attachment,
    search_emails as _search_emails,
)
from gmail_tool import get_gmail_service, send_email, create_draft
from document_parser import parse_attachments


class GmailProvider:
    """Gmail implementation of the EmailProvider plugin interface."""

    name = "gmail"
    display_name = "Google Gmail"
    supported_scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/calendar",
    ]

    # -- Auth helpers -------------------------------------------------------

    def authenticate(self, email: str) -> bool:
        try:
            from auth_test import authenticate_email
            authenticate_email(email)
            return True
        except Exception:
            return False

    def list_authenticated(self) -> list[str]:
        return list_authenticated_emails()

    def is_authenticated(self, email: str) -> bool:
        return is_email_authenticated(email)

    # -- Inbox / email reading ----------------------------------------------

    def _service_for(self, email: Optional[str] = None):
        """Get a Gmail service, optionally for a specific authenticated email."""
        if email:
            creds = get_credentials_for_email(email)
            if creds:
                return get_gmail_service(creds)
        creds = get_credentials()
        return get_gmail_service(creds)

    def list_inbox(self, email: Optional[str] = None, max_results: int = 20,
                   query: Optional[str] = None) -> list[dict]:
        service = self._service_for(email)
        return _list_inbox(service, max_results=max_results, query=query)

    def read_email(self, message_id: str, email: Optional[str] = None) -> dict:
        service = self._service_for(email)
        return _read_email(service, message_id)

    def download_attachment(self, message_id: str, attachment_id: str,
                           email: Optional[str] = None) -> bytes:
        service = self._service_for(email)
        return _download_attachment(service, message_id, attachment_id)

    def search(self, query: str, email: Optional[str] = None,
               max_results: int = 20) -> list[dict]:
        service = self._service_for(email)
        return _search_emails(service, query, max_results=max_results)

    # -- Document parsing (delegates to document_parser) --------------------

    def parse_attachments(self, attachments: list[dict]) -> list[dict]:
        """Parse all attachments from an email, returning extracted text."""
        return parse_attachments(attachments)

    # -- Sending ------------------------------------------------------------

    def send_email(self, to: str, subject: str, body: str,
                   email: Optional[str] = None) -> dict:
        service = self._service_for(email)
        return send_email(service, to, subject, body)

    def create_draft(self, to: str, subject: str, body: str,
                     email: Optional[str] = None) -> dict:
        service = self._service_for(email)
        return create_draft(service, to, subject, body)
