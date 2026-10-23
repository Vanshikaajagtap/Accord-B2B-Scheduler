"""
Document Parser — extracts readable text from common document formats.

Supports: PDF, DOCX, TXT, CSV, JSON.
Used by the Accord B2B Scheduler to read scheduling-related documents
received as email attachments.
"""

import csv
import io
import json
import os
import tempfile
from typing import Optional


def parse_pdf(data: bytes) -> str:
    """Extract text from a PDF file using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(data)
            tmp.flush()
            doc = fitz.open(tmp.name)
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            return "\n".join(text_parts).strip()
    except ImportError:
        return "[PDF parsing unavailable — install PyMuPDF: pip install pymupdf]"
    except Exception as e:
        return f"[PDF parse error: {e}]"


def parse_docx(data: bytes) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        from docx import Document
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=True) as tmp:
            tmp.write(data)
            tmp.flush()
            doc = Document(tmp.name)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs).strip()
    except ImportError:
        return "[DOCX parsing unavailable — install python-docx: pip install python-docx]"
    except Exception as e:
        return f"[DOCX parse error: {e}]"


def parse_txt(data: bytes) -> str:
    """Decode and return plain text content."""
    try:
        return data.decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"[TXT decode error: {e}]"


def parse_csv(data: bytes) -> str:
    """Read CSV and return a human-readable table string."""
    try:
        text = data.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return "[Empty CSV]"
        # Format as simple table
        lines = []
        for i, row in enumerate(rows):
            line = " | ".join(row)
            if i == 0:
                lines.append(line)
                lines.append("-" * len(line))
            else:
                lines.append(line)
        return "\n".join(lines)
    except Exception as e:
        return f"[CSV parse error: {e}]"


def parse_json(data: bytes) -> str:
    """Pretty-print JSON content for readability."""
    try:
        text = data.decode("utf-8", errors="replace")
        obj = json.loads(text)
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        return parse_txt(data)
    except Exception as e:
        return f"[JSON parse error: {e}]"


# Extension → parser mapping
_PARSERS = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".doc": parse_docx,
    ".txt": parse_txt,
    ".md": parse_txt,
    ".csv": parse_csv,
    ".json": parse_json,
}


def parse_document(filename: str, data: bytes) -> str:
    """
    Auto-detect format from filename and extract text.

    Args:
        filename: Original filename (used to detect format).
        data: Raw file bytes.

    Returns:
        Extracted text content, or an error/status message.
    """
    ext = os.path.splitext(filename)[1].lower()
    parser = _PARSERS.get(ext)
    if parser:
        return parser(data)
    return f"[Unsupported file format: {ext}. Supported: {', '.join(_PARSERS.keys())}]"


def parse_attachments(attachments: list[dict]) -> list[dict]:
    """
    Parse a list of attachment dicts (as returned by email_reader.read_email).

    Each dict must have: filename, data (base64-encoded).

    Returns:
        List of dicts with keys: filename, mimeType, text (extracted content).
    """
    import base64
    results = []
    for att in attachments:
        raw_data = base64.urlsafe_b64decode(att.get("data", "")) if att.get("data") else b""
        text = parse_document(att.get("filename", ""), raw_data) if raw_data else "[No data]"
        results.append({
            "filename": att.get("filename", "unknown"),
            "mimeType": att.get("mimeType", ""),
            "text": text,
        })
    return results
