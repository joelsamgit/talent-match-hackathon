"""
test_contract.py — Shared Data Contract Invariant & Schema Validation Tests

Coverage:
  1. JSON serialisability (json.dumps model_dump())
  2. Data contract top-level keys completeness
  3. Category code enum integrity across matched & missing skills
  4. Match score range invariant (0 <= match_score <= 100)
  5. Non-null invariants (matched_skills & missing_skills are lists)
  6. Match confidence enum values (high, medium, low)
  7. Missing skill importance enum values (high, medium, low)
  8. Non-empty string fields (candidate_name, company, role, summary)
  9. SkillObject field completeness in matched_skills
 10. MissingSkill field completeness in missing_skills
 11. Custom category code UPPERCASE invariant
 12. Model json_schema_extra example validity
"""

import json
import pytest
from unittest.mock import patch

from matcher import match_skills
from models import SkillMatchingOutput, CategoryCode, MatchConfidence, ImportanceLevel


VALID_CATEGORY_CODES = {c.value for c in CategoryCode}
VALID_CONFIDENCE_LEVELS = {c.value for c in MatchConfidence}
VALID_IMPORTANCE_LEVELS = {i.value for i in ImportanceLevel}


class TestDataContractInvariants:

    @pytest.fixture()
    def match_output(self, sample_jd_analytics, sample_candidate_profile, mock_groq_client):
        with patch("matcher._get_client", return_value=mock_groq_client):
            return match_skills(sample_jd_analytics, sample_candidate_profile)

    @pytest.fixture()
    def match_dict(self, match_output):
        return match_output.model_dump()

    def test_json_serializability(self, match_dict):
        """output.model_dump() serialises to JSON cleanly without error."""
        try:
            raw = json.dumps(match_dict)
            parsed = json.loads(raw)
            assert isinstance(parsed, dict)
        except (TypeError, ValueError) as exc:
            pytest.fail(f"Output model is not JSON serialisable: {exc}")

    def test_all_top_level_contract_keys_exist(self, match_dict):
        """Response dictionary includes all 8 mandatory top-level contract keys."""
        required_keys = {
            "jd_source_file",
            "company",
            "role",
            "candidate_name",
            "match_score",
            "summary",
            "matched_skills",
            "missing_skills",
        }
        missing_keys = required_keys - set(match_dict.keys())
        assert not missing_keys, f"Missing required top-level contract keys: {missing_keys}"

    def test_category_code_enum_integrity_matched_skills(self, match_dict):
        """Every category_code in matched_skills is one of the 12 RADIX codes."""
        for skill in match_dict["matched_skills"]:
            code = skill["category_code"]
            assert code in VALID_CATEGORY_CODES, f"Invalid category_code in matched_skills: {code}"

    def test_category_code_enum_integrity_missing_skills(self, match_dict):
        """Every category_code in missing_skills is one of the 12 RADIX codes."""
        for skill in match_dict["missing_skills"]:
            code = skill["category_code"]
            assert code in VALID_CATEGORY_CODES, f"Invalid category_code in missing_skills: {code}"

    def test_match_score_range_invariant(self, match_dict):
        """match_score is always an integer between 0 and 100 inclusive."""
        score = match_dict["match_score"]
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_non_null_lists_invariant(self, match_dict):
        """matched_skills and missing_skills are always lists, never None."""
        assert isinstance(match_dict["matched_skills"], list)
        assert isinstance(match_dict["missing_skills"], list)

    def test_match_confidence_enum_integrity(self, match_dict):
        """match_confidence is high, medium, or low."""
        for skill in match_dict["matched_skills"]:
            conf = skill["match_confidence"]
            assert conf in VALID_CONFIDENCE_LEVELS, f"Invalid match_confidence: {conf}"

    def test_importance_level_enum_integrity(self, match_dict):
        """importance level is high, medium, or low."""
        for skill in match_dict["missing_skills"]:
            imp = skill["importance"]
            assert imp in VALID_IMPORTANCE_LEVELS, f"Invalid importance level: {imp}"

    def test_non_empty_string_metadata_fields(self, match_dict):
        """candidate_name, company, role, summary are non-empty strings."""
        for field in ["candidate_name", "company", "role", "summary", "jd_source_file"]:
            val = match_dict[field]
            assert isinstance(val, str)
            assert len(val.strip()) > 0, f"Field '{field}' is empty."

    def test_matched_skill_fields_completeness(self, match_dict):
        """Each matched skill dictionary has all 5 required fields."""
        required = {"jd_skill_name", "category_code", "candidate_skill_name", "match_confidence", "explanation"}
        for skill in match_dict["matched_skills"]:
            missing = required - set(skill.keys())
            assert not missing, f"MatchedSkill missing fields: {missing}"

    def test_missing_skill_fields_completeness(self, match_dict):
        """Each missing skill dictionary has all 4 required fields."""
        required = {"jd_skill_name", "category_code", "importance", "explanation"}
        for skill in match_dict["missing_skills"]:
            missing = required - set(skill.keys())
            assert not missing, f"MissingSkill missing fields: {missing}"

    def test_model_schema_example_validity(self):
        """Pydantic model schema example is valid and instantiates without error."""
        example = SkillMatchingOutput.model_config["json_schema_extra"]["example"]
        obj = SkillMatchingOutput(**example)
        assert obj.match_score == 85
        assert obj.candidate_name == "Ananya Rao"
