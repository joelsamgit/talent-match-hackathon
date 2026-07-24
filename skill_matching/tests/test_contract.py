"""
test_contract.py — Data contract validation tests for SkillMatchingOutput.
"""

import json
import pytest
from unittest.mock import patch
from matcher import match_skills


class TestDataContract:

    @pytest.fixture()
    def match_output(self, sample_jd_analytics, sample_candidate_profile, mock_groq_client):
        with patch("matcher._get_client", return_value=mock_groq_client):
            return match_skills(sample_jd_analytics, sample_candidate_profile)

    def test_json_serializable(self, match_output):
        data = match_output.model_dump()
        dumped = json.dumps(data)
        loaded = json.loads(dumped)
        assert loaded["candidate_name"] == "Ananya Rao"

    def test_required_fields_present(self, match_output):
        data = match_output.model_dump()
        required_keys = {
            "jd_source_file", "company", "role", "candidate_name",
            "match_score", "summary", "matched_skills", "missing_skills"
        }
        assert required_keys.issubset(set(data.keys()))

    def test_matched_skills_shape(self, match_output):
        data = match_output.model_dump()
        for skill in data["matched_skills"]:
            assert "jd_skill_name" in skill
            assert "category_code" in skill
            assert "candidate_skill_name" in skill
            assert "match_confidence" in skill
            assert "explanation" in skill

    def test_missing_skills_shape(self, match_output):
        data = match_output.model_dump()
        for skill in data["missing_skills"]:
            assert "jd_skill_name" in skill
            assert "category_code" in skill
            assert "importance" in skill
            assert "explanation" in skill
