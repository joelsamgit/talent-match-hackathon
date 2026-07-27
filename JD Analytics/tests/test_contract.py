"""
test_contract.py — Data contract validation tests for JDAnalyticsOutput

These tests verify that the output of analyze_jd() ALWAYS satisfies the
shared team data contract, regardless of what the LLM returns.

They are the "trust boundary" tests — if these pass, every other module
(Resume Analyzer, Matching Engine, Frontend) can safely consume the output.

All tests use a mocked Groq client; no real API calls are made.
"""

import json
import pytest
from unittest.mock import patch

from tests.conftest import make_mock_groq_client, MOCK_GROQ_JSON

VALID_CATEGORY_CODES = {"DSA", "COD", "OOD", "APTI", "COMM", "AI", "CLOUD", "SQL", "SWE", "SYSD", "NETW", "OS", "OTHER"}


# ---------------------------------------------------------------------------
# Fixture: a freshly produced JDAnalyticsOutput from a mocked run
# ---------------------------------------------------------------------------

@pytest.fixture()
def output(sample_jd_text):
    """
    Runs analyze_jd() with the mocked Groq client and the sample JD text.
    Returns the JDAnalyticsOutput for contract tests to inspect.
    """
    mock_client = make_mock_groq_client()
    with patch("analyzer._get_client", return_value=mock_client):
        from analyzer import analyze_jd
        return analyze_jd(sample_jd_text, "sample_jd.txt")


@pytest.fixture()
def output_dict(output):
    """The same output serialised to a plain Python dict via .model_dump()."""
    return output.model_dump()


# ---------------------------------------------------------------------------
# Contract Test 1: JSON serialisability
# ---------------------------------------------------------------------------

class TestJsonSerializable:

    def test_output_is_json_serializable(self, output_dict):
        """
        The output must be serialisable to JSON without errors.
        Ensures no non-serialisable types (e.g. Enum instances, datetime)
        leak into the final dict — which would break any frontend or API
        consumer that calls json.dumps() or response.json().
        """
        try:
            serialised = json.dumps(output_dict)
        except (TypeError, ValueError) as exc:
            pytest.fail(f"Output is not JSON serialisable: {exc}")

        # Round-trip check: the serialised string must parse back cleanly
        parsed = json.loads(serialised)
        assert isinstance(parsed, dict)

    def test_skills_list_is_json_serializable(self, output_dict):
        """
        The skills list specifically must serialise to a JSON array cleanly,
        since it is the primary payload consumed by other modules.
        """
        skills_json = json.dumps(output_dict["skills"])
        parsed = json.loads(skills_json)
        assert isinstance(parsed, list)


# ---------------------------------------------------------------------------
# Contract Test 2: category_code enum correctness
# ---------------------------------------------------------------------------

class TestCategoryCodeContract:

    def test_all_category_codes_are_valid(self, output_dict):
        """
        Every category_code in the skills list must be one of the 12 RADIX codes.
        An invalid code would cause a KeyError in the Matching Engine, which uses
        the codes as dict keys for its scoring matrix.
        """
        for i, skill in enumerate(output_dict["skills"]):
            code = skill["category_code"]
            assert code in VALID_CATEGORY_CODES, (
                f"Skill #{i} has invalid category_code '{code}'. "
                f"Allowed: {sorted(VALID_CATEGORY_CODES)}"
            )

    def test_no_null_category_codes(self, output_dict):
        """
        category_code must never be None or an empty string.
        Pydantic should enforce this, but this test pins the behaviour explicitly.
        """
        for skill in output_dict["skills"]:
            assert skill["category_code"] is not None
            assert skill["category_code"].strip() != ""

    def test_category_codes_are_uppercase_strings(self, output_dict):
        """
        All 12 RADIX codes are uppercase alphabetic strings (e.g. 'DSA', 'COMM').
        This test ensures no lowercase variants slip through (e.g. 'dsa').
        """
        for skill in output_dict["skills"]:
            code = skill["category_code"]
            assert code == code.upper(), f"category_code '{code}' is not uppercase"


# ---------------------------------------------------------------------------
# Contract Test 3: confidence enum correctness
# ---------------------------------------------------------------------------

class TestConfidenceContract:

    def test_all_confidence_levels_are_valid(self, output_dict):
        """
        Every confidence value must be 'high', 'medium', or 'low'.
        The frontend renders colour-coded badges using these exact strings.
        Any other value would render as a broken badge.
        """
        for i, skill in enumerate(output_dict["skills"]):
            conf = skill["confidence"]
            assert conf in VALID_CONFIDENCE_LEVELS, (
                f"Skill #{i} has invalid confidence '{conf}'. "
                f"Allowed: {VALID_CONFIDENCE_LEVELS}"
            )

    def test_no_null_confidence(self, output_dict):
        """confidence must never be None or empty."""
        for skill in output_dict["skills"]:
            assert skill["confidence"] is not None
            assert skill["confidence"].strip() != ""


# ---------------------------------------------------------------------------
# Contract Test 4: source_type invariant
# ---------------------------------------------------------------------------

class TestSourceTypeContract:

    def test_source_type_is_always_jd(self, output_dict):
        """
        source_type must always equal 'jd' for outputs from this service.
        The Matching Engine uses this to verify it's consuming a JD output
        (not a resume output), and will reject mismatched types.
        """
        assert output_dict["source_type"] == "jd", (
            f"source_type must be 'jd', got: {output_dict['source_type']!r}"
        )

    def test_source_type_is_not_resume(self, output_dict):
        """
        Explicit negative check: source_type must never be 'resume'.
        Both types share the same schema shape, so this test pins the
        discriminator field value for JD Analytics specifically.
        """
        assert output_dict["source_type"] != "resume"

    def test_source_type_is_not_none(self, output_dict):
        """source_type must never be None — it is a required string field."""
        assert output_dict["source_type"] is not None


# ---------------------------------------------------------------------------
# Contract Test 5: skills list invariant
# ---------------------------------------------------------------------------

class TestSkillsListContract:

    def test_skills_is_always_a_list(self, output_dict):
        """
        skills must always be a Python list (never None, never a dict).
        Downstream modules iterate over skills with a for-loop — a None
        would raise TypeError and crash the matching pipeline.
        """
        assert isinstance(output_dict["skills"], list), (
            f"skills must be a list, got: {type(output_dict['skills']).__name__}"
        )

    def test_skills_is_not_none(self, output_dict):
        """
        skills must never be None. Even an empty list is acceptable;
        None is not, because it indicates a parsing failure rather than
        a JD with no detectable skills.
        """
        assert output_dict["skills"] is not None

    def test_each_skill_has_four_required_fields(self, output_dict):
        """
        Every skill object must have all four contract fields.
        This is the schema validation that other modules depend on —
        if any field is missing, the matching engine will KeyError.
        """
        required_fields = {"skill_name", "category_code", "evidence", "confidence"}
        for i, skill in enumerate(output_dict["skills"]):
            missing = required_fields - set(skill.keys())
            assert not missing, (
                f"Skill #{i} is missing required fields: {missing}. "
                f"Got: {set(skill.keys())}"
            )

    def test_no_duplicate_skill_names(self, output_dict):
        """
        The same skill should not appear twice in the list under an identical
        skill_name. Duplicates would double-count skills in the matching score.
        This test uses the mock output which is deterministic, so duplicates
        here would indicate a bug in the Pydantic model or parser.
        """
        names = [s["skill_name"] for s in output_dict["skills"]]
        assert len(names) == len(set(names)), (
            f"Duplicate skill_names found: {[n for n in names if names.count(n) > 1]}"
        )
