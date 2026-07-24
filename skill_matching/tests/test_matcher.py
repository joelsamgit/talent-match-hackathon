"""
test_matcher.py — Unit tests for matcher.py with mocked Groq API.
"""

import pytest
from unittest.mock import patch
from matcher import match_skills
from models import SkillMatchingOutput
from tests.conftest import make_mock_groq_client


class TestMatcherUnit:

    def test_match_skills_returns_output_model(self, sample_jd_analytics, sample_candidate_profile):
        mock_client = make_mock_groq_client()
        with patch("matcher._get_client", return_value=mock_client):
            output = match_skills(sample_jd_analytics, sample_candidate_profile)

        assert isinstance(output, SkillMatchingOutput)
        assert output.candidate_name == "Ananya Rao"
        assert output.company == "Google LLC"
        assert output.role == "Software Engineer (SWE)"
        assert len(output.matched_skills) == 3
        assert len(output.missing_skills) == 1
        assert 0 <= output.match_score <= 100

    def test_fallback_on_api_error(self, sample_jd_analytics, sample_candidate_profile):
        """If LLM call raises an exception, matcher should fall back to deterministic matcher."""
        mock_client = make_mock_groq_client()
        mock_client.chat.completions.create.side_effect = Exception("Groq API Timeout")

        with patch("matcher._get_client", return_value=mock_client):
            output = match_skills(sample_jd_analytics, sample_candidate_profile)

        assert isinstance(output, SkillMatchingOutput)
        assert output.candidate_name == "Ananya Rao"
        assert 0 <= output.match_score <= 100
