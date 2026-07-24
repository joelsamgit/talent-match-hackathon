"""
test_api.py — Integration tests for the FastAPI routes in main.py

Uses FastAPI's TestClient (backed by httpx) to exercise routes end-to-end.
The Groq client is monkeypatched via the `test_client` fixture in conftest.py
so no real API calls are made.

Routes tested:
  GET  /health
  GET  /samples
  POST /analyze           (file upload)
  POST /analyze-text      (JSON body)
  POST /analyze-sample/   (bundled sample)
"""

import io
import json
import pytest

from tests.conftest import make_docx_bytes, make_pdf_bytes


VALID_CATEGORY_CODES = {"DSA", "COD", "OOD", "SYSD", "OS", "NETW", "DB", "SWE", "DATA", "APTI", "COMM", "MGMT"}


# ---------------------------------------------------------------------------
# Shared assertion helper
# ---------------------------------------------------------------------------

def assert_valid_output_shape(body: dict) -> None:
    """
    Assert that a response body matches the shared data contract.
    Centralised here so changes to the contract only require updating one place.
    """
    assert body["source_type"] == "jd", f"source_type should be 'jd', got {body['source_type']!r}"
    assert "source_file" in body
    assert "company" in body
    assert "role" in body
    assert isinstance(body["skills"], list)

    for skill in body["skills"]:
        assert "skill_name" in skill
        assert "category_code" in skill
        assert "evidence" in skill
        assert "confidence" in skill
        assert skill["category_code"] in VALID_CATEGORY_CODES, (
            f"Unknown category_code: {skill['category_code']!r}"
        )
        assert skill["confidence"] in {"high", "medium", "low"}


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:

    def test_health_returns_200(self, test_client):
        """
        GET /health must return HTTP 200. Used by Docker health checks,
        CI pipelines, and the integrator's smoke test.
        """
        response = test_client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self, test_client):
        """
        The response body must contain {"status": "ok"}.
        Other modules and the integrator rely on this exact shape.
        """
        response = test_client.get("/health")
        body = response.json()
        assert body["status"] == "ok"

    def test_health_returns_version_field(self, test_client):
        """
        version field must be present. Useful for the integrator to confirm
        which build is running during the hackathon demo.
        """
        response = test_client.get("/health")
        body = response.json()
        assert "version" in body


# ---------------------------------------------------------------------------
# GET /samples
# ---------------------------------------------------------------------------

class TestSamplesEndpoint:

    def test_samples_returns_200(self, test_client):
        """GET /samples must succeed even if the samples directory is empty."""
        response = test_client.get("/samples")
        assert response.status_code == 200

    def test_samples_returns_list_and_count(self, test_client):
        """
        The response must have both 'samples' (a list) and 'count' (an int).
        The /analyze-sample route depends on this list to validate filenames.
        """
        response = test_client.get("/samples")
        body = response.json()
        assert isinstance(body["samples"], list)
        assert isinstance(body["count"], int)
        assert body["count"] == len(body["samples"])


# ---------------------------------------------------------------------------
# POST /analyze — file upload
# ---------------------------------------------------------------------------

class TestAnalyzeDocxUpload:

    def test_valid_docx_returns_200(self, test_client):
        """
        Upload a minimal in-memory DOCX. Should return HTTP 200.
        Smoke test for the full DOCX upload pipeline.
        """
        docx_bytes = make_docx_bytes("We need strong DSA and system design skills")
        response = test_client.post(
            "/analyze",
            files={"file": ("test_jd.docx", io.BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert response.status_code == 200

    def test_valid_docx_returns_correct_shape(self, test_client):
        """
        The DOCX upload response body must match the shared data contract.
        Tests that the full pipeline (extract → analyze → validate) produces
        the expected JSON shape.
        """
        docx_bytes = make_docx_bytes("We need strong DSA and system design skills")
        response = test_client.post(
            "/analyze",
            files={"file": ("test_jd.docx", io.BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        body = response.json()
        assert_valid_output_shape(body)

    def test_valid_docx_source_type_is_jd(self, test_client):
        """
        source_type in the response must always be 'jd' regardless of the
        uploaded file type. Other modules use this field to distinguish JD vs
        resume outputs.
        """
        docx_bytes = make_docx_bytes("Software engineer role at ACME Corp")
        response = test_client.post(
            "/analyze",
            files={"file": ("jd.docx", io.BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert response.json()["source_type"] == "jd"

    def test_valid_docx_skills_list_non_empty(self, test_client):
        """
        The skills list in the response must not be empty. The mocked Groq
        client always returns a non-empty skill list, so this confirms the
        mock is wired into the API correctly.
        """
        docx_bytes = make_docx_bytes("Requires Python, algorithms, and communication")
        response = test_client.post(
            "/analyze",
            files={"file": ("jd.docx", io.BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert len(response.json()["skills"]) > 0


class TestAnalyzePdfUpload:

    def test_valid_pdf_returns_200(self, test_client):
        """
        Upload a minimal in-memory PDF. Should return HTTP 200.
        Validates the PDF extraction branch of the upload pipeline.
        """
        pdf_bytes = make_pdf_bytes("Requires strong knowledge of networking and OS")
        response = test_client.post(
            "/analyze",
            files={"file": ("test_jd.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 200

    def test_valid_pdf_returns_correct_shape(self, test_client):
        """
        PDF upload response body must match the shared data contract.
        Exercises the pdfplumber extraction path end-to-end.
        """
        pdf_bytes = make_pdf_bytes("Python, SQL, REST API experience required")
        response = test_client.post(
            "/analyze",
            files={"file": ("test_jd.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert_valid_output_shape(response.json())


# ---------------------------------------------------------------------------
# POST /analyze — error cases
# ---------------------------------------------------------------------------

class TestAnalyzeErrors:

    def test_unsupported_file_type_returns_400(self, test_client):
        """
        Uploading a .txt file should return HTTP 400 (Bad Request) because
        only .pdf and .docx are supported. Tests that the file-type guard
        fires before text extraction is attempted.
        """
        response = test_client.post(
            "/analyze",
            files={"file": ("resume.txt", io.BytesIO(b"some plain text"), "text/plain")},
        )
        assert response.status_code == 400
        assert "Unsupported" in response.json()["detail"] or "unsupported" in response.json()["detail"].lower()

    def test_missing_file_returns_422(self, test_client):
        """
        Sending a POST to /analyze with no file attached should return HTTP 422
        (Unprocessable Entity) — FastAPI's automatic validation for missing
        required form fields.
        """
        response = test_client.post("/analyze")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /analyze-text
# ---------------------------------------------------------------------------

class TestAnalyzeText:

    def test_valid_text_body_returns_200(self, test_client):
        """
        POST /analyze-text with a valid JSON body containing 'text' should
        return HTTP 200. This endpoint is the integration point for Role 3
        (Profile Builder) which pre-extracts text before sending it here.
        """
        response = test_client.post(
            "/analyze-text",
            json={
                "text": "We are looking for a Software Engineer with strong DSA and system design skills.",
                "filename": "test.txt",
            },
        )
        assert response.status_code == 200

    def test_valid_text_body_returns_correct_shape(self, test_client):
        """
        The /analyze-text response must match the same data contract as /analyze.
        Both endpoints feed into the same matching engine — schema consistency
        is critical.
        """
        response = test_client.post(
            "/analyze-text",
            json={
                "text": "Strong knowledge of SQL, OOP, and cloud infrastructure required.",
                "filename": "jd_from_profile_builder.txt",
            },
        )
        assert_valid_output_shape(response.json())

    def test_empty_text_returns_400(self, test_client):
        """
        Sending an empty 'text' field should return HTTP 400. Prevents the
        API from forwarding an empty string to the LLM and wasting a token quota.
        """
        response = test_client.post(
            "/analyze-text",
            json={"text": "", "filename": "empty.txt"},
        )
        assert response.status_code == 400

    def test_whitespace_only_text_returns_400(self, test_client):
        """
        Whitespace-only text is treated as empty — same as blank input.
        Happens when a PDF is image-only (scanned) and the extractor returns
        only whitespace.
        """
        response = test_client.post(
            "/analyze-text",
            json={"text": "   \n\t  ", "filename": "scanned.pdf"},
        )
        assert response.status_code == 400

    def test_missing_text_field_returns_422(self, test_client):
        """
        If the request body is missing the required 'text' field, FastAPI's
        Pydantic validation should return 422. Tests that model validation
        runs before any business logic.
        """
        response = test_client.post(
            "/analyze-text",
            json={"filename": "no_text.txt"},
        )
        assert response.status_code == 422
