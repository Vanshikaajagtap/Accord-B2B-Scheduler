"""
Accord Email Plugin System

Provides a provider-agnostic interface for reading emails and parsing documents.
New email providers (Outlook, IMAP, etc.) can be added by implementing the
EmailProvider base class and registering with the plugin registry.

Usage:
    from accord.plugins import get_provider, list_providers

    gmail = get_provider("gmail")
    inbox = gmail.list_inbox(query="is:unread")
    email = gmail.read_email(message_id)
    docs  = gmail.parse_attachments(email["attachments"])
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmailProvider(Protocol):
    """
    Interface that every email provider plugin must satisfy.

    Methods mirror the core capabilities needed by Accord:
    reading inbox, searching, reading a single email, downloading
    attachments, and parsing attached documents.
    """

    name: str
    display_name: str
    supported_scopes: list[str]

    def authenticate(self, email: str) -> bool:
        """Authenticate a user. Return True on success."""
        ...

    def list_authenticated(self) -> list[str]:
        """Return a list of currently authenticated email addresses."""
        ...

    def is_authenticated(self, email: str) -> bool:
        """Check whether a specific email has valid credentials."""
        ...

    def list_inbox(self, max_results: int = 20, query: str | None = None) -> list[dict]:
        """List emails from the inbox."""
        ...

    def read_email(self, message_id: str) -> dict:
        """Read full email content including body and attachments."""
        ...

    def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Download raw attachment bytes."""
        ...

    def search(self, query: str, max_results: int = 20) -> list[dict]:
        """Search emails using provider-specific query syntax."""
        ...

    def send_email(self, to: str, subject: str, body: str) -> dict:
        """Send an email. Returns a result dict."""
        ...

    def create_draft(self, to: str, subject: str, body: str) -> dict:
        """Create a draft email. Returns a draft dict."""
        ...


# ---------------------------------------------------------------------------
# Plugin Registry
# ---------------------------------------------------------------------------

_registry: dict[str, EmailProvider] = {}


def register_provider(provider: EmailProvider) -> None:
    """Register an email provider plugin."""
    _registry[provider.name] = provider


def get_provider(name: str) -> EmailProvider:
    """Retrieve a registered provider by name."""
    if name not in _registry:
        available = ", ".join(_registry.keys()) or "(none)"
        raise KeyError(f"Provider '{name}' not registered. Available: {available}")
    return _registry[name]


def list_providers() -> list[dict]:
    """Return metadata about all registered providers."""
    return [
        {"name": p.name, "display_name": p.display_name, "scopes": p.supported_scopes}
        for p in _registry.values()
    ]


# Auto-register built-in providers on import
def _register_defaults():
    try:
        from accord.plugins.gmail_provider import GmailProvider
        register_provider(GmailProvider())
    except Exception:
        pass  # Gmail provider dependencies not installed — skip silently


_register_defaults()
