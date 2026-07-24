"""
extractor.py — PDF and DOCX text extraction utilities.

Dispatch table:
  .pdf   → pdfplumber
  .docx  → python-docx
  other  → ValueError

Usage:
    text = extract_text("Google LLC - Software Engineer.pdf", file_bytes)
"""

from __future__ import annotations

import io
from pathlib import Path


def extract_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF byte stream using pdfplumber."""
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError(
            "pdfplumber is not installed. Run: pip install pdfplumber"
        ) from exc

    text_parts: list[str] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())

    return "\n\n".join(text_parts)


def extract_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from a DOCX byte stream using python-docx."""
    try:
        from docx import Document
    except ImportError as exc:
        raise RuntimeError(
            "python-docx is not installed. Run: pip install python-docx"
        ) from exc

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text(filename: str, file_bytes: bytes) -> str:
    """
    Dispatch to the correct extractor based on file extension.

    Args:
        filename:   Original filename (used for extension detection only).
        file_bytes: Raw file content as bytes.

    Returns:
        Extracted plain text string.

    Raises:
        ValueError: If the file extension is not .pdf or .docx.
        RuntimeError: If the required extraction library is missing.
    """
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        text = extract_from_pdf(file_bytes)
    elif suffix in (".docx", ".doc"):
        text = extract_from_docx(file_bytes)
    else:
        raise ValueError(
            f"Unsupported file type: '{suffix}'. Only .pdf and .docx are accepted."
        )

    if not text.strip():
        raise ValueError(
            f"Could not extract any text from '{filename}'. "
            "The file may be scanned/image-based or corrupt."
        )

    return text
