"""
tests/test_resume_parsing.py — Smoke tests for the full resume-parsing pipeline.

Tests run against every file in data/sample_resumes/ (if any exist).
LLM output varies run-to-run, so we print results for manual review
rather than asserting exact values. We DO assert structural invariants
(valid schema, correct types, no crashes).

Also includes edge-case tests for:
  - Empty file upload
  - Wrong file extension
  - Corrupted/unreadable content
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app
from schema import ParseResult


client = TestClient(app)

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_resumes"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _print_parse_result(filename: str, result: dict):
    """Pretty-print a parse result for manual review."""
    print(f"\n{'='*60}")
    print(f"FILE: {filename}")
    print(f"{'='*60}")
    print(f"Extraction method: {result.get('extraction_method')}")
    print(f"Warnings: {result.get('warnings', [])}")

    skills = result.get("skills", {}).get("skills", [])
    print(f"\nSkills ({len(skills)}):")
    for s in skills:
        print(f"  [{s['category_code']}] {s['skill_name']} "
              f"(conf={s['confidence']}) — \"{s['evidence']}\"")

    fields = result.get("fields", {})
    print(f"\nStructured Fields:")
    for key in ["name", "email", "education", "experience_years_estimate"]:
        print(f"  {key}: {fields.get(key)}")

    projects = fields.get("projects", [])
    print(f"  projects ({len(projects)}):")
    for p in projects:
        print(f"    - {p.get('title', '?')}: {p.get('description', '?')[:80]}")

    internships = fields.get("internships", [])
    print(f"  internships ({len(internships)}): {internships}")

    certs = fields.get("certifications", [])
    print(f"  certifications ({len(certs)}): {certs}")
    print()


# ---------------------------------------------------------------------------
# Tests against sample resumes (skip if directory is empty / no API keys)
# ---------------------------------------------------------------------------

def _get_sample_files() -> list[Path]:
    """Collect all PDF/DOCX files from the sample directory."""
    if not SAMPLE_DIR.exists():
        return []
    return sorted(
        p for p in SAMPLE_DIR.iterdir()
        if p.suffix.lower() in (".pdf", ".docx") and p.is_file()
    )


_sample_files = _get_sample_files()

_has_api_key = bool(
    os.environ.get("GROQ_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
)


@pytest.mark.skipif(not _sample_files, reason="No sample resumes in data/sample_resumes/")
@pytest.mark.skipif(not _has_api_key, reason="No LLM API key set (GROQ_API_KEY or GEMINI_API_KEY)")
@pytest.mark.parametrize("sample_path", _sample_files, ids=[p.name for p in _sample_files])
def test_full_pipeline_on_samples(sample_path: Path):
    """Run the full pipeline on each sample resume and print results."""
    with open(sample_path, "rb") as f:
        response = client.post(
            "/parse-resume",
            files={"file": (sample_path.name, f, "application/octet-stream")},
        )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()
    _print_parse_result(sample_path.name, data)

    # Structural assertions (not value assertions — LLM output varies)
    result = ParseResult(**data)
    assert result.extraction_method in ("text", "ocr", "mixed")
    assert isinstance(result.skills.skills, list)
    assert isinstance(result.fields, object)
    assert isinstance(result.warnings, list)


# ---------------------------------------------------------------------------
# Edge-case tests (always run, no API key needed)
# ---------------------------------------------------------------------------

def test_unsupported_file_type():
    """Uploading a .txt file should return 400."""
    response = client.post(
        "/parse-resume",
        files={"file": ("resume.txt", b"some text content", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_empty_file():
    """Uploading an empty file should return 400."""
    response = client.post(
        "/parse-resume",
        files={"file": ("resume.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_corrupted_pdf():
    """Uploading garbage bytes as a PDF should not crash — should return 200 with warnings."""
    response = client.post(
        "/parse-resume",
        files={"file": ("corrupted.pdf", b"not a real pdf", "application/pdf")},
    )
    # Should either be 200 with warnings or gracefully handled
    assert response.status_code == 200
    data = response.json()
    assert len(data.get("warnings", [])) > 0, "Expected warnings for corrupted file"
    print("\nCorrupted PDF result:", json.dumps(data, indent=2)[:500])


def test_corrupted_docx():
    """Uploading garbage bytes as a DOCX should not crash — should return 200 with warnings."""
    response = client.post(
        "/parse-resume",
        files={"file": ("bad.docx", b"not a real docx", "application/octet-stream")},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data.get("warnings", [])) > 0
    print("\nCorrupted DOCX result:", json.dumps(data, indent=2)[:500])


# ---------------------------------------------------------------------------
# Unit tests for extraction layer (no API key needed)
# ---------------------------------------------------------------------------

def test_extraction_unsupported():
    """extract_text should warn on unsupported extensions."""
    from extraction import extract_text

    result = extract_text(b"hello", "resume.jpg")
    assert any("Unsupported" in w for w in result.warnings)


def test_section_mapper_empty():
    """map_sections should return full_document for empty input."""
    from section_mapper import map_sections

    result = map_sections([])
    assert result == {"full_document": ""}


def test_section_mapper_no_headers():
    """map_sections should return full_document when no headers detected."""
    from extraction import TextLine
    from section_mapper import map_sections

    lines = [TextLine(text=f"Line {i}", font_size=10) for i in range(5)]
    result = map_sections(lines)
    assert "full_document" in result


def test_health_check():
    """Health endpoint should be alive."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
