"""
test_analyzer.py — Unit tests for analyzer.py

All tests mock the Groq client — NO real API calls are made.
The Groq dependency is patched at `analyzer._get_client` so the
production HTTP call is fully replaced with a deterministic MagicMock.

Test coverage:
  - Valid JD text → correct JDAnalyticsOutput structure
  - Company and role fields extracted from LLM response
  - Malformed LLM JSON → RuntimeError (not silent failure)
  - Empty input text → ValueError before any API call is made
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from tests.conftest import make_mock_groq_client, MOCK_GROQ_JSON

# Valid category codes defined in models.py
VALID_CATEGORY_CODES = {"DSA", "COD", "OOD", "SYSD", "OS", "NETW", "DB", "SWE", "DATA", "APTI", "COMM", "MGMT"}
VALID_CONFIDENCE_LEVELS = {"high", "medium", "low"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_groq(json_payload: dict | None = None):
    """
    Context manager that patches analyzer._get_client to return a mock
    Groq client whose completions return `json_payload` as a JSON string.
    """
    mock_client = make_mock_groq_client(json_payload)
    return patch("analyzer._get_client", return_value=mock_client)


# ---------------------------------------------------------------------------
# Test: valid JD text produces correct output structure
# ---------------------------------------------------------------------------

class TestAnalyzeJdStructure:

    def test_returns_jd_analytics_output_type(self, sample_jd_text):
        """
        Verifies that analyze_jd() returns a JDAnalyticsOutput instance
        (not a raw dict, not None). Ensures Pydantic validation runs.
        """
        from models import JDAnalyticsOutput

        with _patch_groq():
            from analyzer import analyze_jd
            result = analyze_jd(sample_jd_text, "sample_jd.txt")

        assert isinstance(result, JDAnalyticsOutput)

    def test_source_type_is_always_jd(self, sample_jd_text):
        """
        source_type must always equal 'jd' for this service.
        Other modules use this field to identify which role produced the output.
        """
        with _patch_groq():
            from analyzer import analyze_jd
            result = analyze_jd(sample_jd_text, "sample_jd.txt")

        assert result.source_type == "jd"

    def test_source_file_matches_filename_arg(self, sample_jd_text):
        """
        source_file should echo back exactly the filename passed to analyze_jd().
        Required by the data contract so the frontend can display the filename.
        """
        with _patch_groq():
            from analyzer import analyze_jd
            result = analyze_jd(sample_jd_text, "my_test_jd.pdf")

        assert result.source_file == "my_test_jd.pdf"

    def test_skills_list_is_present_and_non_empty(self, sample_jd_text):
        """
        The skills list must be a non-empty list. An empty list would indicate
        the LLM found nothing (unlikely for a valid JD) and would break the
        downstream matching engine.
        """
        with _patch_groq():
            from analyzer import analyze_jd
            result = analyze_jd(sample_jd_text, "sample_jd.txt")

        assert isinstance(result.skills, list)
        assert len(result.skills) > 0

    def test_every_skill_has_required_fields(self, sample_jd_text):
        """
        Every SkillObject in the skills list must have all four required fields:
        skill_name, category_code, evidence, confidence.
        Missing fields would break the frontend skill cards.
        """
        with _patch_groq():
            from analyzer import analyze_jd
            result = analyze_jd(sample_jd_text, "sample_jd.txt")

        for skill in result.skills:
            assert skill.skill_name, f"skill_name is empty: {skill}"
            assert skill.category_code, f"category_code is missing: {skill}"
            assert skill.evidence, f"evidence is empty: {skill}"
            assert skill.confidence, f"confidence is missing: {skill}"

    def test_all_category_codes_are_valid_enum_values(self, sample_jd_text):
        """
        Every category_code must be one of the 12 RADIX codes.
        Hallucinated codes (e.g. 'ALGO', 'MISC') would break the matching engine
        which relies on the enum for weighted scoring.
        """
        with _patch_groq():
            from analyzer import analyze_jd
            result = analyze_jd(sample_jd_text, "sample_jd.txt")

        for skill in result.skills:
            assert skill.category_code.value in VALID_CATEGORY_CODES, (
                f"Invalid category_code '{skill.category_code}' — "
                f"must be one of {VALID_CATEGORY_CODES}"
            )

    def test_all_confidence_levels_are_valid(self, sample_jd_text):
        """
        confidence must be one of: 'high', 'medium', 'low'.
        Invalid values would break frontend UI components that render
        colour-coded confidence badges.
        """
        with _patch_groq():
            from analyzer import analyze_jd
            result = analyze_jd(sample_jd_text, "sample_jd.txt")

        for skill in result.skills:
            assert skill.confidence.value in VALID_CONFIDENCE_LEVELS, (
                f"Invalid confidence '{skill.confidence}' — "
                f"must be one of {VALID_CONFIDENCE_LEVELS}"
            )

    def test_raw_text_length_is_populated(self, sample_jd_text):
        """
        raw_text_length should reflect the character count of the input text.
        It's used for debugging token usage and detecting truncation.
        """
        with _patch_groq():
            from analyzer import analyze_jd
            result = analyze_jd(sample_jd_text, "sample_jd.txt")

        assert result.raw_text_length is not None
        assert result.raw_text_length > 0


# ---------------------------------------------------------------------------
# Test: company and role extraction
# ---------------------------------------------------------------------------

class TestCompanyRoleExtraction:

    def test_company_and_role_from_llm_response(self, sample_jd_text):
        """
        company and role should come directly from the LLM's JSON response,
        not be hardcoded or inferred from the filename when the LLM provides them.
        Confirms the parsing path for these top-level fields works correctly.
        """
        payload = {
            "company": "Google LLC",
            "role": "Software Engineer",
            "skills": [MOCK_GROQ_JSON["skills"][0]],
        }

        with _patch_groq(payload):
            from analyzer import analyze_jd
            result = analyze_jd(sample_jd_text, "sample_jd.txt")

        assert result.company == "Google LLC"
        assert result.role == "Software Engineer"

    def test_company_fallback_from_filename(self, sample_jd_text):
        """
        If the LLM returns empty strings for company/role, the analyzer falls back
        to parsing the filename (e.g. 'Google LLC - Software Engineer.pdf').
        Ensures the fallback logic works so output is never completely blank.
        """
        payload = {
            "company": "",
            "role": "",
            "skills": [MOCK_GROQ_JSON["skills"][0]],
        }

        with _patch_groq(payload):
            from analyzer import analyze_jd
            result = analyze_jd(sample_jd_text, "Microsoft - Data Analyst.pdf")

        # Either the LLM value or the filename-derived fallback
        assert result.company  # must not be empty
        assert result.role     # must not be empty


# ---------------------------------------------------------------------------
# Test: malformed LLM response
# ---------------------------------------------------------------------------

class TestMalformedLlmResponse:

    def test_invalid_json_raises_runtime_error(self, sample_jd_text):
        """
        If the LLM returns malformed JSON (despite json_object mode), analyze_jd()
        must raise RuntimeError with a clear message. This lets the API return a
        502 to the client instead of crashing the server with an unhandled exception.
        """
        # Build a mock that returns garbage content
        mock_message = MagicMock()
        mock_message.content = "This is NOT valid JSON {broken"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("analyzer._get_client", return_value=mock_client):
            from analyzer import analyze_jd
            with pytest.raises(RuntimeError, match="invalid JSON"):
                analyze_jd(sample_jd_text, "sample_jd.txt")

    def test_missing_skills_key_returns_empty_list(self, sample_jd_text):
        """
        If the LLM omits the 'skills' key entirely, analyze_jd() should return
        an output with an empty skills list rather than crashing. The .get() default
        in the parser handles this — this test pins that behaviour.
        """
        payload = {"company": "Test Corp", "role": "Engineer"}  # no 'skills' key

        with _patch_groq(payload):
            from analyzer import analyze_jd
            result = analyze_jd(sample_jd_text, "sample_jd.txt")

        assert result.skills == []


# ---------------------------------------------------------------------------
# Test: empty input text validation
# ---------------------------------------------------------------------------

class TestEmptyInput:

    def test_empty_string_raises_value_error(self):
        """
        analyze_jd('') must raise ValueError immediately — before _get_client()
        is even called. This prevents unnecessary API calls for empty uploads
        and gives the API layer a chance to return 422 instead of 502.
        """
        from analyzer import analyze_jd

        with pytest.raises(ValueError, match="empty"):
            analyze_jd("", "empty.txt")

    def test_whitespace_only_raises_value_error(self):
        """
        A string of only whitespace/newlines should be treated as empty.
        Some PDFs extract to whitespace-only strings when the document is
        image-only (scanned). This test pins that edge case.
        """
        from analyzer import analyze_jd

        with pytest.raises(ValueError, match="empty"):
            analyze_jd("   \n\t\n   ", "scanned.pdf")

    def test_valid_text_does_not_raise(self, sample_jd_text):
        """
        Confirm the empty-text guard does NOT fire for normal JD text.
        Regression guard — ensure we didn't make the check too aggressive.
        """
        with _patch_groq():
            from analyzer import analyze_jd
            result = analyze_jd(sample_jd_text, "sample_jd.txt")

        assert result is not None
